from qgis.PyQt.QtWidgets import QMessageBox
from pathlib import Path
import pandas as pd
import chardet
import math
import glob
import os

def showErrorMessage(message):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Error")
        msg_box.setText(message)
        msg_box.exec_()

def compute_averages(df):
        numeric_columns = df.select_dtypes(include=['number']).columns
        exclude_columns = ["MEAN_X", "MEAN_Y"]
        if exclude_columns:
            numeric_columns = [column for column in numeric_columns if column not in exclude_columns]
        averages = {column: df[column].mean() for column in numeric_columns}
        return averages

def compute_totals(self, df):
    totals = {'X3.7.03.1': df['X3.7.03.1'].sum()}
    return totals

def process(dlg):
    # get all the inputs
    csvFolder = dlg.CSVFolderLineEdit.text()
    evaluationSheet= dlg.EvaluationSheetLineEdit.text()
    sheetName = dlg.SheetNameComboBox.currentText()
    outputFolder = dlg.OutputLineEdit.text()

    if csvFolder and evaluationSheet and sheetName and outputFolder:
        print('All the inputs have been provided')
        csvFiles = glob.glob(os.path.join(csvFolder,'*.csv'))
        try:
            evSheet = pd.read_excel(evaluationSheet, sheet_name=sheetName)
            avgColumns = evSheet['Analysis Column Code'].where((evSheet['Function code']=='A') | (evSheet['Function code']=='A , T'))
            totalsColumns = evSheet['Analysis Column Code'].where((evSheet['Function code']=='A , T'))
            cleanedAvgColumns = [x for x in list(avgColumns) if not (isinstance(x, float) and math.isnan(x))]
            cleanedTotalsColumns = [x for x in list(totalsColumns) if not (isinstance(x, float) and math.isnan(x))]
            if csvFiles:
                try:
                    averagesDF = pd.DataFrame()
                    totalsDF = pd.DataFrame()
                    count = 0
                    for csvFile in csvFiles:
                        detectedFile=chardet.detect(Path(csvFile).read_bytes())
                        df = pd.read_csv(csvFile,encoding=detectedFile['encoding'])
                        
                        finalAvgColumns = [item for item in cleanedAvgColumns if item in df.columns]
                        finalAvgColumns.insert(0,'RSP_ID')
                        finalTotalsColumns = [item for item in cleanedTotalsColumns if item in df.columns]
                        finalTotalsColumns.insert(0,'RSP_ID')
                        
                        totals = {}
                        averages = {}
                        averages['RSP_ID']=df['RSP_ID'].iloc[0]
                        totals['RSP_ID'] = df['RSP_ID'].iloc[0]
                        
                        # Compute averages
                        for item in finalAvgColumns:
                            try:
                                if item=='RSP_ID':
                                    continue
                                else:
                                    averages[item]=df[item].mean()
                            except TypeError as e:
                                averages[item]='Invalid data type'
                                
                        #Compute totals
                        for item in finalTotalsColumns:
                            try:
                                if item=='RSP_ID':
                                    continue
                                else:
                                    totals[item]=df[item].sum()
                            except TypeError as e:
                                totals[item]='Invalid data type'
                        
                        # Save averages to dataframe
                        if len(averagesDF.columns) != 0:  
                            averagesDF.loc[len(averagesDF.index)]=averages
                        else:
                            for key in averages.keys():
                                averagesDF[key]=averages[key]

                        #Save totals to dataframe
                        if len(totalsDF.columns) != 0:  
                            totalsDF.loc[len(totalsDF.index)]=totals
                        else:
                            for key in totals.keys():
                                totalsDF[key]=totals[key]
                        
                        count +=1
                        dlg.progressBar.setValue(int((count/len(csvFiles))*100))
                    # Save computations to file  
                    averagesDF.to_csv(f"{outputFolder}/Averages.csv")
                    totalsDF.to_csv(f"{outputFolder}/Totals.csv")
                except FileNotFoundError as e:
                    print('Error found')
            else:
                showErrorMessage('There are no CSV files in the folder provided')
                
        except Exception as e:
            showErrorMessage(str(e))
    else:
        showErrorMessage("Please provide all inputs as required")