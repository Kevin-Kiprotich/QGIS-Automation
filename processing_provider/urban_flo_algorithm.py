# -*- coding: utf-8 -*-

"""
/***************************************************************************
 UrbanFlo
                                 A QGIS plugin
 This plugin automates activity space creation
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2024-04-29
        copyright            : (C) 2024 by Kevin Kiprotich
        email                : kevinkiprotich0089@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'Kevin Kiprotich'
__date__ = '2024-04-29'
__copyright__ = '(C) 2024 by Kevin Kiprotich'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'
import shutil
import subprocess
import numpy as np
import csv
import os
import processing
import gc
from pathlib import Path
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsProcessing,
                       QgsVectorLayer,
                       QgsProject,
                       QgsFeatureSink,
                       QgsProcessingAlgorithm,
                       QgsProcessingException,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterString,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterNumber,
                       QgsLayerTreeGroup,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterFolderDestination,
                       QgsProcessingParameterField,
                       QgsCoordinateReferenceSystem
                       )

try:
    import pandas as pd
    import geopandas as gpd
    import openpyxl
    import chardet
except ImportError:
    # Install pandas using subprocess
    subprocess.check_call(['pip', 'install', 'pandas'])
    subprocess.check_call(['pip', 'install', 'openpyxl'])
    subprocess.check_call(['pip', 'install', 'geopandas'])
    subprocess.check_call(['pip', 'install', 'chardet'])
    import pandas as pd
    import geopandas as gpd
    import chardet
# finally:
#     import pandas as pd


class UrbanFloAlgorithm(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    OUTPUT = 'OUTPUT'
    SEGMENT = 'SEGMENT'
    SHEET_NAME="SHEET_NAME"
    ROAD="ROAD"
    CONDITION="CONDITION"
    BUFFER="BUFFER"
    BUFFERSIZE="BUFFER_SIZE"
    ROUTE="ROUTE"
    FOLDER="FOLDER"
    USECOST = "USECOST"
    USECOST_COLUMN = "USECOST_COLUMN"

    
    
    

    def addMapLayer(self,layer_path,layer_name):
        layer = QgsVectorLayer(layer_path, layer_name, "ogr")
        if not layer.isValid():
            print(f"Layer '{layer_name}' failed to load!")
            return None
        else:
            # Get the layer tree root
            root = QgsProject.instance().layerTreeRoot()
            QgsProject.instance().addMapLayer(layer)
            

    
    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It can have any kind of
        # geometry.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.SEGMENT,
                self.tr('Segments'),
                [QgsProcessing.TypeVectorPoint]
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.ROAD,
                self.tr('Road Network'),
                [QgsProcessing.TypeVectorLine]
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.CONDITION,
                self.tr('Condition Sheet'),
                [QgsProcessing.TypeFile]
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.USECOST,
                self.tr('Use cost'),
                defaultValue=False
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.USECOST_COLUMN,
                self.tr('Cost column'),
                parentLayerParameterName=self.ROAD,

                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.BUFFERSIZE,
                self.tr('Buffer size (metres)'),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.0
            )
        )
       
        # get the path to the folder that you will use to store the outputs
        default_folder=os.path.join(os.getenv('USERPROFILE'),'Documents')
        self.addParameter(
           QgsProcessingParameterFolderDestination(
               self.FOLDER,
               self.tr('Output Folder'),
               defaultValue=default_folder
           )
       )
    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        # create variables tp hold the outputs
        
        outputs={}
        
        segment = self.parameterAsSource(parameters,self.SEGMENT, context)
        output_folder=self.parameterAsString(parameters,self.FOLDER,context)
        feedback.reportError(f"USE COST:\t{parameters['USECOST']}")

        #Create folders to store all the data that is recieved from the models
        steiner_path=os.path.join(output_folder,'Steiner_routes')
        buffer_path=os.path.join(output_folder,'Buffers')
        activity_space_path=os.path.join(output_folder,'Activity Spaces')
        csv_path=os.path.join(output_folder, "csvs")
        averages_path=os.path.join(output_folder, "Averages")
        totals_path=os.path.join(output_folder, "Totals")
        temporary_path=os.path.join(output_folder, "Temp")

        if not os.path.exists(steiner_path):
            os.makedirs(steiner_path)
        if not os.path.exists(buffer_path):
            os.makedirs(buffer_path)
        if not os.path.exists(activity_space_path):
            os.makedirs(activity_space_path)
        if not os.path.exists(csv_path):
            os.makedirs(csv_path)
        if not os.path.exists(averages_path):
            os.makedirs(averages_path)
        if not os.path.exists(totals_path):
            os.makedirs(totals_path)
        if not os.path.exists(temporary_path):
            os.makedirs(temporary_path)
        

        if parameters['USECOST']:
            if not parameters['ROAD']:
                raise QgsProcessingException(self.tr("Road file is required when 'Use cost' is True"))
            if not parameters['USECOST_COLUMN']:
                raise QgsProcessingException(self.tr("Use cost column must be selected when 'Use cost' is True"))
            
        def evaluateCost(cond):
            if cond:
                return parameters['USECOST_COLUMN']
            else:
                return ''

        try:
            df=pd.read_excel(parameters['CONDITION'])
            AVG = {'RSP': []}
            count = 0
            avg_count = 0

            TOT = {'RSP': []}
            for index, row in df.iterrows():
                results={}
                respondent=row["Respd_ID"]
                rspid=respondent
                respondent=respondent.replace("/","_")
                respondent=respondent.replace(":","_")
                segments=row["X3.8.9"]
                segment_list=segments.split(",")
                segment_list=list(filter(None,segment_list))
                if not segment_list:
                    continue
                sql_query=""
                for segment in segment_list:
                    sql_query += f'"is_segment" = \'{segment.strip()}\' OR\n'
                
                expression = sql_query[:-4]
                feedback.pushConsoleInfo(expression)
                print(expression)
                alg_params = {
                'EXPRESSION': expression,
                'INPUT': parameters['SEGMENT'],
                'OUTPUT':QgsProcessing.TEMPORARY_OUTPUT  # creating new selection
                }
                feedback.pushConsoleInfo(parameters['USECOST_COLUMN'])
                outputs['ExtractByExpression'] = processing.run('native:extractbyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                alg_params = {
                '-g': False,
                'GRASS_MIN_AREA_PARAMETER': 0.0001,
                'GRASS_OUTPUT_TYPE_PARAMETER': 0,  # auto
                'GRASS_REGION_PARAMETER': None,
                'GRASS_SNAP_TOLERANCE_PARAMETER': -1,
                'GRASS_VECTOR_DSCO': '',
                'GRASS_VECTOR_EXPORT_NOCAT': False,
                'GRASS_VECTOR_LCO': '',
                'acolumn': evaluateCost(parameters['USECOST']),
                'arc_type': [0,1],  # line,boundary
                'input': parameters['ROAD'],
                'npoints': -1,
                'points': outputs['ExtractByExpression']['OUTPUT'],
                'terminal_cats': '1-100000',
                'threshold': 50,
                'output':  os.path.join(temporary_path, f"{respondent}.shp"),
                }
                outputs['Vnetsteiner'] = processing.run('grass7:v.net.steiner', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                # Add the output layer to the map canvas
                # results['Route']=outputs['Vnetsteiner']['output']

                feedback.pushConsoleInfo("Steiner path computed successfully")
                # Add field to attributes table
                alg_params = {
                    'FIELD_ALIAS': '',
                    'FIELD_COMMENT': '',
                    'FIELD_LENGTH': 75,
                    'FIELD_NAME': 'RSP_ID',
                    'FIELD_PRECISION': 0,
                    'FIELD_TYPE': 2,  # Text (string)
                    'INPUT': outputs['Vnetsteiner']['output'],
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
                outputs['AddFieldToAttributesTable_ROUTE'] = processing.run('native:addfieldtoattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                # results['ActivitySpace']=outputs['AddFieldToAttributesTable']['OUTPUT']
                alg_params = {
                    'FIELD_LENGTH': 100,
                    'FIELD_NAME': 'RSP_ID',
                    'FIELD_PRECISION': 0,
                    'FIELD_TYPE': 2,  # Text (string)
                    'FORMULA': f"'{rspid}'",
                    'INPUT': outputs['AddFieldToAttributesTable_ROUTE']['OUTPUT'],
                    'OUTPUT': os.path.join(steiner_path,f"{respondent}.shp")
                }
                outputs['FieldCalculator_ROUTE'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

                feedback.pushConsoleInfo("Steiner Attribute added")

                #BUFFERING
                alg_params = {
                    'DISSOLVE': True,
                    'DISTANCE': parameters["BUFFER_SIZE"],
                    'END_CAP_STYLE': 0,  # Round
                    'INPUT': outputs['FieldCalculator_ROUTE']['OUTPUT'],
                    'JOIN_STYLE': 0,  # Round
                    'MITER_LIMIT': 2,
                    'SEGMENTS': 5,
                    'SEPARATE_DISJOINT': False,
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }

                outputs['Buffer'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                results['Buffer'] = outputs['Buffer']['OUTPUT']

                feedback.pushConsoleInfo("Buffer created")


                # Add field to attributes table
                alg_params = {
                    'FIELD_ALIAS': '',
                    'FIELD_COMMENT': '',
                    'FIELD_LENGTH': 75,
                    'FIELD_NAME': 'RSP_ID',
                    'FIELD_PRECISION': 0,
                    'FIELD_TYPE': 2,  # Text (string)
                    'INPUT': outputs['Buffer']['OUTPUT'],
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
                outputs['AddFieldToAttributesTable_BUFFER'] = processing.run('native:addfieldtoattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                # results['ActivitySpace']=outputs['AddFieldToAttributesTable']['OUTPUT']
                alg_params = {
                    'FIELD_LENGTH': 100,
                    'FIELD_NAME': 'RSP_ID',
                    'FIELD_PRECISION': 0,
                    'FIELD_TYPE': 2,  # Text (string)
                    'FORMULA': f"'{rspid}'",
                    'INPUT': outputs['AddFieldToAttributesTable_BUFFER']['OUTPUT'],
                    'OUTPUT': os.path.join(buffer_path,f"{respondent}.shp")
                }
                outputs['FieldCalculator_BUFFER'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

                feedback.pushConsoleInfo("Buffer attribute added")

                # Clip
                alg_params = {
                    'INPUT': parameters['SEGMENT'],
                    'OVERLAY': outputs['FieldCalculator_BUFFER']['OUTPUT'],
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
                outputs['Clip'] = processing.run('native:clip', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                # results['Clip'] = outputs['Clip']['OUTPUT']

                # Add field to attributes table
                alg_params = {
                    'FIELD_ALIAS': '',
                    'FIELD_COMMENT': '',
                    'FIELD_LENGTH': 75,
                    'FIELD_NAME': 'RSP_ID',
                    'FIELD_PRECISION': 0,
                    'FIELD_TYPE': 2,  # Text (string)
                    'INPUT': outputs['Clip']['OUTPUT'],
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
                outputs['AddFieldToAttributesTable'] = processing.run('native:addfieldtoattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                # results['ActivitySpace']=outputs['AddFieldToAttributesTable']['OUTPUT']
                alg_params = {
                    'FIELD_LENGTH': 100,
                    'FIELD_NAME': 'RSP_ID',
                    'FIELD_PRECISION': 0,
                    'FIELD_TYPE': 2,  # Text (string)
                    'FORMULA': f"'{rspid}'",
                    'INPUT': outputs['AddFieldToAttributesTable']['OUTPUT'],
                    'OUTPUT': os.path.join(activity_space_path,f"{respondent}.shp")
                }
                outputs['FieldCalculator'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                results['ActivitySpace'] = outputs['FieldCalculator']['OUTPUT']

                # Save vector features to file
                alg_params = {
                    'ACTION_ON_EXISTING_FILE': 0,  # Create or overwrite file
                    'DATASOURCE_OPTIONS': '',
                    'INPUT': outputs['FieldCalculator']['OUTPUT'],
                    'LAYER_NAME': '',
                    'LAYER_OPTIONS': '',
                    'OUTPUT': os.path.join(csv_path,f"{respondent}.csv")
                }
                outputs['SaveVectorFeaturesToFile'] = processing.run('native:savefeatures', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                results['Csv'] = outputs['SaveVectorFeaturesToFile']['OUTPUT']
            
            return results

        except Exception as e:
            feedback.reportError('Error reading file:{}'.format(e))
            return {}
        
        finally:
            # Explicitly delete variables to release memory
            del outputs, segment, output_folder, steiner_path, buffer_path
            del activity_space_path, csv_path, averages_path, totals_path, temporary_path
            del df, AVG, TOT, results, respondent, rspid, segments, segment_list
            del sql_query, expression, alg_params
            
            gc.collect()
        
        # Return the results of the algorithm. In this case our only result is
        # the feature sink which contains the processed features, but some
        # algorithms may return multiple feature sinks, calculated numeric
        # statistics, etc. These should all be included in the returned
        # dictionary, with keys matching the feature corresponding parameter
        # or output names.
        # return {self.OUTPUT: dest_id}

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Create Urban Activity Space'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return ''

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return UrbanFloAlgorithm()