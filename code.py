from sets import Set
from datetime import datetime

from qgis._core import QgsMessageLog, QgsMapLayerRegistry, QgsFeatureRequest
from PyQt4.QtCore import QFileSystemWatcher

filewatcher=None
logTag="OpenGIS"
excelName="Beispiel"
excelKeyName="Field1"
areaKey="Field9"
centroidKey="Field14"
shpName="Beispiel_Massnahmepool"
shpKeyName="ef_key"

#TODO: initial sync between excel and shp?

shpAdd = Set([])
shpChange = {}
shpRemove = Set([])


def reload_excel():
    layer = layer_from_name(excelName)
    layer.dataProvider().forceReload()

def get_fk_set(layerName, fkName, skipFirst=True, fids=None):
    layer = layer_from_name(layerName)
    freq = QgsFeatureRequest()
    if fids is not None:
        freq.setFilterFids(fids)
    feats = [f for f in layer.getFeatures(freq)]
    fkSet = []
    first=True
    for f in feats:
        if skipFirst and first:
            first=False
            continue
        fk = f.attribute(fkName)
        fkSet.append(fk)
    return fkSet
        

def layer_from_name(layerName):
    # Important: If multiple layers with same name exist, it will return the first one it finds
    for (id, layer) in QgsMapLayerRegistry.instance().mapLayers().iteritems():
        if unicode(layer.name()) == layerName:
            return layer
    return None


def info(msg):
    QgsMessageLog.logMessage(str(msg), logTag, QgsMessageLog.INFO)

def warn(msg):
    QgsMessageLog.logMessage(str(msg), logTag)

def error(msg):
    QgsMessageLog.logMessage(str(msg), logTag, QgsMessageLog.CRITICAL)

def excel_changed():
    info("Excel changed in disk")
    reload_excel()
    update_shp_from_excel()

def added_geom(layerId, fids):
    fks_to_add = get_fk_set(shpName,shpKeyName,skipFirst=False,fids=fids)
    global shpAdd
    shpAdd = Set(fks_to_add)

def removed_geom(layerId, fids):
    fks_to_remove = get_fk_set(shpName,shpKeyName,skipFirst=False,fids=fids)
    global shpRemove
    shpRemove = Set(fks_to_remove)

def changed_geom(layerId, geoms):
    fids = geoms.keys()
    freq = QgsFeatureRequest() 
    freq.setFilterFids(fids)
    feats = list(layer_from_name(shpName).getFeatures(freq))
    fks_to_change = get_fk_set(shpName,shpKeyName,skipFirst=False,fids=fids)
    global shpChange
    shpChange = {k:v for (k,v) in zip(fks_to_change, feats)}
    info("changed"+str(shpChange))

def update_excel_from_shp():
    info("Will now update excel from edited shapefile")
    info(shpChange)
    info(shpAdd)
    info(shpRemove)
    layer = layer_from_name(excelName)
    shp = layer_from_name(shpName)
    layer.startEditing()
    feats = [f for f in layer.getFeatures()]

    for f in feats:
        key = f.attribute(excelKeyName)
        if key in shpRemove:
            layer.deleteFeature(f.id())
        if key in shpChange.keys():
           shpf = shpChange[key]
           f.setAttribute(areaKey, str(shpf.geometry().area()))
           f.setAttribute(centroidKey, str(shpf.geometry().centroid().asPoint()))
           info("Set {} area to {}".format(key,str(shpf.geometry().area() )))

    for newf in shpAdd:
        pass

    layer.commitChanges()
    global shpAdd
    global shpChange
    global shpRemove
    shpAdd = Set([])
    shpChange = {}
    shpRemove = Set([]) 


def updateShpLayer(fksToRemove):
    layer = layer_from_name(shpName)
    feats = [f for f in layer.getFeatures()]
    layer.startEditing()
    for f in feats:
         if f.attribute(shpKeyName) in fksToRemove:
             layer.deleteFeature(f.id())
    layer.commitChanges()
     

def update_shp_from_excel():
    info("Excel updated. Need to edit shapefile accordingly!")
    excelFks = Set(get_fk_set(excelName, excelKeyName,skipFirst=True))
    shpFks = Set(get_fk_set(shpName,shpKeyName,skipFirst=False))
    # TODO somewhere here I should refresh the join
    # TODO also special warning if shp layer is in edit mode
    info("Keys in excel"+str(excelFks))
    info("Keys in shp"+str(shpFks))
    if shpFks==excelFks:
        info("Excel and Shp layer have the same rows. No update necessary")
        return
    inShpButNotInExcel = shpFks - excelFks
    inExcelButNotInShp = excelFks - shpFks
    if inExcelButNotInShp:
         warn("There are rows in the excel file with no matching geometry {}. Can't update shapefile from those.".format(inExcelButNotInShp))
    if inShpButNotInExcel:
        info("Will remove features "+str(inShpButNotInExcel)+"from shapefile because they have been removed from excel")
        updateShpLayer(inShpButNotInExcel)

def handle_connections(filename):
    global filewatcher # otherwise the object is lost
    filewatcher = QFileSystemWatcher([filename])
    filewatcher.fileChanged.connect(excel_changed)
    shpLayer = layer_from_name(shpName)
    shpLayer.committedFeaturesAdded.connect(added_geom)
    shpLayer.committedFeaturesRemoved.connect(removed_geom)
    shpLayer.committedGeometriesChanges.connect(changed_geom)
    shpLayer.editingStopped.connect(update_excel_from_shp)


handle_connections("/home/carolinux/Projects/Beispiel/Mappe2.xlsx")