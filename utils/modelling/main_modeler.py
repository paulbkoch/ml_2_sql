import pickle
import random
import numpy as np 

from sklearn.model_selection import train_test_split
from utils.modelling.performance import *
from utils.modelling.calibration import *

# The actual algorithms (grey as we refer to them dynamically)
from utils.modelling.models import ebm
from utils.modelling.models import decision_rule
from utils.modelling.models import decision_tree
from utils.modelling.models import l_regression

def make_model(given_name, datasets, model_name, model_type, model_params, post_params, logging):
    """
    Train and save a model, and generate performance plots.

    Parameters
    ----------
    given_name : str
        The name of the model.
    datasets : dict
        A dictionary containing the training and test datasets.
    model_name : str
        The name of the model to be used.
    model_type : str
        The type of the model (classification or regression).
    model_params : dict
        A dictionary containing the hyperparameters of the model.
    post_params : dict
        A dictionary containing the postprocessing parameters.
    logging : logger
        A logger object used for logging.

    Returns
    -------
    A trained machine learning model that can be used to make predictions on new data.

    """
    # unpack datasets
    X_train = datasets['cv_train']['X']
    y_train = datasets['cv_train']['y']
    X_test = datasets['cv_test']['X']
    y_test = datasets['cv_test']['y']
    X_all = datasets['final_train']['X']
    y_all = datasets['final_train']['y']


    # check if X is a list (CV should be applied in that case)
    if isinstance(X_train, list):
        y_test_pred_list = list()
        y_test_prob_list = list()
        y_test_list = y_test

        for fold_id in range(len(X_train)):
            print('Train model on test data')
            logging.info('Train model on test data')

            # Check if model needs to be calibrated
            if post_params['calibration'] != 'false':
                X_slice_train, X_cal, y_slice_train, y_cal = train_test_split(X_train[fold_id],y_train[fold_id], test_size=0.2,random_state=random.randint(0,100))
            else:
                X_slice_train, y_slice_train = X_train[fold_id], y_train[fold_id]

            clf = globals()[model_name].trainModel(X_slice_train, y_slice_train, model_params, model_type, logging)

            if post_params['calibration'] != 'false':
                clf = calibrateModel(clf, X_cal, y_cal, logging, method=post_params['calibration'], final_model=False)

            # discrete predictions
            y_test_pred_list.append(clf.predict(X_test[fold_id]))

            if model_type == 'classification':
            # probability predictions
                # Binary classification
                if len(clf.classes_) == 2:
                    y_test_prob_list.append(clf.predict_proba(X_test[fold_id])[:,1])
                elif len(clf.classes_) > 2:
                    y_test_prob_list.append(clf.predict_proba(X_test[fold_id]))

        # Merge list of prediction lists into one list
        y_test_pred = np.concatenate(y_test_pred_list, axis=0)

        if model_type == 'classification':
            # Merge list of prediction probabilities lists into one list
            y_test_prob = np.concatenate(y_test_prob_list, axis=0)

        y_test = np.concatenate(y_test, axis=0)

    # If just regular train/test split has been applied
    else:
        clf = globals()[model_name].trainModel(X_train, y_train, model_params, model_type, logging)

        # discrete prediction
        y_test_pred = clf.predict(X_test)

        if model_type == 'classification':
            # probability prediction
            y_test_prob = clf.predict_proba(X_test)[:,1]

    # train model one last time on all samples (upsampled)
    print('Train final model on all data')
    logging.info('Train final model on all data')

    # Check if model needs to be calibrated
    if post_params['calibration'] != 'false':
        X_all, X_cal, y_all, y_cal = train_test_split(X_all, y_all, test_size=0.2, random_state=123)

    clf = globals()[model_name].trainModel(X_all, y_all, model_params, model_type, logging)

    # Save model in pickled format
    filename = f'{given_name}/model/{model_name}_{model_type}.sav'
    pickle.dump(clf, open(filename, 'wb'))

    # train set prediction of final model
    y_all_pred = clf.predict(X_all)

    if model_type == 'classification':
    # probability predictions
        # Binary classification
        if len(clf.classes_) == 2:
            y_all_prob = clf.predict_proba(X_all)[:,1]
        elif len(clf.classes_) > 2:
            y_all_prob = clf.predict_proba(X_all)


    if post_params['calibration'] != 'false':
        cal_clf, cal_reg = calibrateModel(clf, X_cal, y_cal, logging, method=post_params['calibration'], final_model=True)

        # Save model in pickled format
        filename = given_name + '/model/ebm_calibrated_{model_type}.sav'.format(model_type=model_type)
        pickle.dump(cal_clf, open(filename, 'wb'))

        # train set prediction of final model
        y_all_pred = cal_clf.predict(X_all)

        if model_type == 'classification':
            # probability predictions
            # Binary classification
            if len(clf.classes_) == 2:
                y_all_prob = clf.predict_proba(X_all)[:, 1]
            elif len(clf.classes_) > 2:
                y_all_prob = clf.predict_proba(X_all)


    # Performance and other post modeling plots
    if model_type == 'classification':
        # Threshold dependant
        plotConfusionMatrix(given_name, y_all, y_all_prob, y_all_pred, post_params['file_type'], data_type='final_train', logging=logging)
        plotConfusionMatrix(given_name, y_test, y_test_prob, y_test_pred, post_params['file_type'], data_type='test', logging=logging)

        if len(clf.classes_) == 2:
            # Also create pr curve for class 0
            y_all_neg = np.array([1 - j for j in list(y_all)])
            y_all_prob_neg = np.array([1 - j for j in list(y_all_prob)])

            y_test_list_neg = [[1 - j for j in i] for i in y_test_list]
            y_test_prob_list_neg = [[1 - j for j in i] for i in y_test_prob_list]

            # Threshold independant
            plotClassificationCurve(given_name, y_all, y_all_prob, curve_type='roc', data_type='final_train', logging=logging)
            plotClassificationCurve(given_name, y_test_list, y_test_prob_list, curve_type='roc', data_type='test', logging=logging)

            plotClassificationCurve(given_name, y_all, y_all_prob, curve_type='pr', data_type='final_train_class1', logging=logging)
            plotClassificationCurve(given_name, y_all_neg, y_all_prob_neg, curve_type='pr', data_type='final_train_class0', logging=logging)

            plotClassificationCurve(given_name, y_test_list, y_test_prob_list, curve_type='pr', data_type='test_data_class1', logging=logging)
            plotClassificationCurve(given_name, y_test_list_neg, y_test_prob_list_neg, curve_type='pr', data_type='test_data_class0', logging=logging)

            plotCalibrationCurve(given_name, y_all, y_all_prob, data_type='final_train', logging=logging)
            plotCalibrationCurve(given_name, y_test_list, y_test_prob_list, data_type='test', logging=logging)

            plotProbabilityDistribution(given_name, y_all, y_all_prob, data_type='final_train', logging=logging)
            plotProbabilityDistribution(given_name, y_test, y_test_prob, data_type='test', logging=logging)

        # If multiclass classification
        elif len(clf.classes_) > 2:
            # loop through classes
            for c in clf.classes_:
                # creating a list of all the classes except the current class
                other_class = [x for x in clf.classes_ if x != c]

                # Get index of selected class in clf.classes_
                class_index = list(clf.classes_).index(c)

                # marking the current class as 1 and all other classes as 0
                y_test_list_ova = [[0 if x in other_class else 1 for x in fold_] for fold_ in y_test_list]
                y_test_prob_list_ova = [[x[class_index] for x in fold_] for fold_ in y_test_prob_list]

                # concatonate probs together to one list for distribution plot
                y_test_ova = np.concatenate(y_test_list_ova, axis=0)
                y_test_prob_ova = np.concatenate(y_test_prob_list_ova, axis=0)

                y_all_ova = [0 if x in other_class else 1 for x in y_all]
                y_all_prob_ova = [x[class_index] for x in y_all_prob]


                # Threshold independant
                # plotClassificationCurve(given_name, y_all_ova, y_all_prob_ova, curve_type='roc', data_type=f'final_train_class_'{c}, logging=logging)
                plotClassificationCurve(given_name, y_test_list_ova, y_test_prob_list_ova, curve_type='roc', data_type=f'test_class_{c}', logging=logging)

                # plotClassificationCurve(given_name, y_all_ova, y_all_prob_ova, curve_type='pr', data_type='final_train_class1', logging=logging)
                plotClassificationCurve(given_name, y_test_list_ova, y_test_prob_list_ova, curve_type='pr', data_type=f'test_class_{c}', logging=logging)

                # multiClassPlotCalibrationCurvePlotly(given_name, y_all, pd.DataFrame(y_all_prob, columns=clf.classes_), title='fun')
                plotCalibrationCurve(given_name, y_test_list_ova, y_test_prob_list_ova, data_type=f'test_class_{c}', logging=logging)

                # plotProbabilityDistribution(given_name, y_all_ova, y_all_prob_ova, data_type='final_train', logging=logging)
                plotProbabilityDistribution(given_name, y_test_ova, y_test_prob_ova, data_type=f'test_class_{c}', logging=logging)

    # if regression
    elif model_type == 'regression':
        plotYhatVsYSave(given_name, y_test, y_test_pred, data_type='test')
        plotYhatVsYSave(given_name, y_all, y_all_pred, data_type='final_train')

        adjustedR2 = 1 - (1 - clf.score(X_all, y_all)) * (len(y_all) - 1) / (len(y_all) - X_all.shape[1] - 1)
        print('Adjusted R2: {adjustedR2}'.format(adjustedR2=adjustedR2))
        logging.info('Adjusted R2: {adjustedR2}'.format(adjustedR2=adjustedR2))

    # Post modeling plots, specific per model but includes feature importance among others
    globals()[model_name].postModelPlots(clf, given_name + '/feature_importance', post_params['file_type'], logging)

    return clf
