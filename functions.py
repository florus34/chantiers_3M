import pandas as pd
import geopandas as gpd
from shapely import Polygon, MultiPolygon, MultiLineString, union_all
from datetime import date
import streamlit as st
import plotly.express as px
import requests
import io
import os
from streamlit_option_menu import option_menu

# set variable
today = pd.to_datetime(date.today()) # set today to datetime64 format

# chargement de la donnée brute en json
@st.cache_data
def load_chantiers():
  url = "https://data.montpellier3m.fr/sites/default/files/ressources/MMM_MMM_HistoriqueChantiersLineaire.json"
  df = pd.read_json(url)
  return df

def delete_history(df):
  df = df.query("etape not in ['Fermé','Réfectionné']")
  df.reset_index(drop=True, inplace=True)
  return df

# préparation du dataset
@st.cache_data
def format_dataset(df,del_history=True):

  def get_attributes(df):
    attributes = [dico['properties'] for dico in df['features'].to_list()]
    return pd.DataFrame.from_records(attributes)

  def type_columns(df):
    df['debut_chan'] = pd.to_datetime(df['debut_chan'])
    df['fin_chanti'] = pd.to_datetime(df['fin_chanti'])
    return df

  def get_geometry(df):

    def get_features_geom(df):
      features = df['features'].to_list()
      attributes_geom = list()
      for dico in features :
        if dico['geometry'] is not None:
          attributes_geom.append(dico['geometry'])
        else:
          attributes_geom.append({'type':'vide','coordinates':'vide'})
      geom = pd.DataFrame.from_records(attributes_geom)

      return geom

    def construct_geom(geom):
      geometry_list = list()
      for idx in geom.index:
        if geom['type'][idx]=='Polygon':
          geometry_list.append(Polygon(geom['coordinates'][idx][0]))
        elif geom['type'][idx]=='MultiPolygon':
          try:
            geometry_list.append(MultiPolygon(geom['coordinates'][idx]))
          except:
            Mline1 = MultiLineString(geom['coordinates'][idx][0])
            Mline2 = MultiLineString(geom['coordinates'][idx][1])
            Mline = union_all([Mline1,Mline2])
            geometry_list.append(Mline)
        else:
          geometry_list.append(Polygon())

      return geometry_list
    
    geom = get_features_geom(df)
    geometry_list = construct_geom(geom)
    geometry = pd.DataFrame(geometry_list,columns=['geometry'])
    
    return geometry

  # create attributes columns
  df_t = get_attributes(df)
  print (f"étape create attributes : {df_t.shape}")

  # create geometry column
  geometry = get_geometry(df)
  print (f"construct geometry : {geometry.shape}")

  # concat attributes columns with geometry column
  df_t = pd.concat([df_t,geometry], axis=1)
  print (f"étape concat : {df_t.shape}")

  # delete history
  if del_history:
    df_t = delete_history(df_t)
    print (f"étape delete history : {df_t.shape}")

  # format columns to datetime
  df_t = type_columns(df_t)

  # declare to gdf
  df_t = gpd.GeoDataFrame(df_t, geometry='geometry', crs='wgs84')
  print (f"étape construct gdf : {df_t.shape}")

  return df_t

# préparation des contrôleurs du dataset
def set_controllers(df):
  # set today to datetime64 format
  today = pd.to_datetime(date.today())
  # set controls
  control_1 = df.loc[(df['etape']=='Ouvert') & (df['fin_chanti']<today)]
  control_2 = df.loc[(~df['etape'].isin(['Ouvert','Fermé','Réfectionné'])) & (df['fin_chanti'] < today)]
  control_3 = df.loc[(~df['etape'].isin(['Ouvert','Fermé','Réfectionné'])) & (df['debut_chan'] <= today) & (df['fin_chanti'] >= today)]
  control_4 = df.loc[df['debut_chan']>df['fin_chanti']]

  controllers = {'open_expired': control_1,
                 'instruction_expired': control_2,
                 'instruction_current': control_3,
                 'negative_period' : control_4     
  }
  
  return controllers

# calcul des contrôleurs
def get_controllers(df):
  def summarize_controllers(dic):
    summarize = {k:len(v) for (k,v) in dic.items()}
    return summarize

  def format_summarize(dic):
    # get value
    value = list(dic.values())
    # get index
    index = list(dic.keys())
    # set name column
    col = ['count']
    # create df
    df = pd.DataFrame(data=value, index=index, columns=col)
    
    return df

  controllers = set_controllers(df)
  summarize = summarize_controllers(controllers)
  get_controllers = format_summarize(summarize)

  return get_controllers

# correction du dataset
def get_fix_data(df,del_history=True):
  df = df.copy()
  # fix control_1
  df.loc[(df['etape']=='Ouvert') & (df['fin_chanti'] < today),'etape'] = 'Fermé'
  # fix control_2
  df.loc[(~df['etape'].isin(['Ouvert','Fermé','Réfectionné'])) & (df['fin_chanti'] < today), 'etape'] = 'Fermé'
  # fix control_3
  df.loc[(~df['etape'].isin(['Ouvert','Fermé','Réfectionné'])) & (df['debut_chan'] <= today) & (df['fin_chanti'] >= today), 'etape'] = 'Ouvert'
  # fix control_4
  df_result = df.copy()
  mask = df['debut_chan']>df['fin_chanti']
  s1 = df.query("debut_chan > fin_chanti")['debut_chan']
  s2 = df.query("debut_chan > fin_chanti")['fin_chanti']
  df_result.loc[mask,'debut_chan']=s2
  df_result.loc[mask,'fin_chanti']=s1
  if del_history :
    # delete history
    df_result = delete_history(df_result)
  return df_result

# calcul des indicateurs
def get_indicators(df):
  count_open = df.query("etape == 'Ouvert'").shape[0]
  count_inst = df.query("etape != 'Ouvert'").shape[0]
  indicators = {
      'open':count_open,
      'inst':count_inst
  }
  return indicators

# get gdf from df_json
def get_shape(df_json):
  prop = [dic['properties'] for dic in df_json['features'].to_list()]
  prop = pd.DataFrame.from_records(prop)
  geom = [dic['geometry'] for dic in df_json['features'].to_list()]
  geom = pd.DataFrame.from_records(geom)
  shape = pd.concat([prop,geom],axis=1)
  shape['geometry'] = shape['coordinates'].map(lambda x : Polygon(x[0]))
  shape = gpd.GeoDataFrame(shape, geometry='geometry', crs='wgs84')
  shape = shape.drop(columns=['type','coordinates'])
  return shape

# count point into polygons
def count_point_into_poly(gs_pt,gs_pol,gs_attr):
  result = dict()
  list_shape = gs_pol.to_crs('2154').to_list()
  list_com = gs_attr.to_list()
  for poly, attr in zip(list_shape,list_com):
    count_point = poly.contains(gs_pt[~gs_pt.is_empty]).sum()
    result[attr]=count_point
  idx = result.keys()
  val = result.values()
  result_df = pd.DataFrame(val,index=idx,columns=['count'])
  return result_df

# count chantier by sectors
def get_chant_by_sectors(chantiers):
  @st.cache_data
  def get_sectors():
    def load_shape_sectors():
      url_quar = 'https://data.montpellier3m.fr/sites/default/files/ressources/VilleMTP_MTP_Quartiers.json'
      url_com = 'https://data.montpellier3m.fr/sites/default/files/ressources/MMM_MMM_PolesZonage.json'
      url_squar = "https://data.montpellier3m.fr/sites/default/files/ressources/VilleMTP_MTP_SousQuartiers.json"
      quar = get_shape(pd.read_json(url_quar))
      com = get_shape(pd.read_json(url_com))
      squar = get_shape(pd.read_json(url_squar))
      return quar,com,squar

    def prepare_sectors(quar,com,squar):
      # quartier mtp
      quar = quar.query("name != 'Centre'") # on supprime le quartier centre
      quar = quar.rename(columns={'name':'nom'})
      quar['secteur']='Montpellier'
      del quar['commune']
      quar['codcomm']= '340172'
      # communes 3M
      com = com.query("nom != 'MONTPELLIER'") # on supprime commune Mtp
      com = com.rename(columns={'POLE':'secteur'})
      # sous-quartier mtp
      squar = squar.query("quartier=='Centre'") # on garde que squar du centre
      squar = squar.rename(columns={'name':'nom', 'quartier':'secteur'})
      del squar['commune']
      squar['codcomm']='340172'
      squar = squar.query("secteur=='Centre'").reset_index(drop=True)
      return quar, com, squar

    def concat_sectors(quar,com,squar):
      sectors = pd.concat([com,quar,squar],axis=0).reset_index(drop=True)
      return sectors
    
    def format_sectors(sectors):
      sectors['nom'] = sectors['nom'].map(lambda x: x.capitalize())
      return sectors

    quar,com, squar = load_shape_sectors()
    quar,com, squar = prepare_sectors(quar,com,squar)
    sectors = concat_sectors(quar,com,squar)
    sectors = format_sectors(sectors)
    return sectors

  sectors = get_sectors()
  # define centroid of chantier
  gs_pt = chantiers.to_crs('2154').centroid
  # define geom of sectors
  gs_pol = sectors['geometry'].to_crs('2154')
  # define sector attribute name
  gs_attr = sectors['nom']

  count = count_point_into_poly(gs_pt=gs_pt,gs_pol=gs_pol,gs_attr=gs_attr)
  count = count.reset_index(names='nom')
  chant_by_sectors = sectors.merge(count, on='nom')
  chant_by_sectors = chant_by_sectors.set_index('nom')

  return chant_by_sectors

def get_map(gdf):
  fig = px.choropleth_mapbox(gdf, geojson=gdf['geometry'], locations=gdf.index, color='count',
                           color_continuous_scale="Viridis",
                          #  range_color=(0, 20),
                           mapbox_style="carto-positron",
                          #  mapbox_style="open-street-map",
                           zoom=9.5, center = {"lat": 43.6099, "lon": 3.8783},
                           opacity=0.5,
                           labels={
                              'nom':'',
                              'count':'Nbre de chantier'}
                          )
  fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
  return fig

def get_sunb(df):
    df.copy()
    df = df.reset_index()
    del df['geometry']
    count = df.query("secteur=='Centre'")['count'].sum()
    row = pd.DataFrame(columns=df.columns, data=[['Centre','340172','Montpellier',count]])
    df = pd.concat([df,row], axis=0)
    df = df.query("secteur!='Centre'")
    df = df.reset_index(drop=True)
    fig = px.sunburst(df,path=['secteur','nom'],values='count')
    return fig
# get plot lines : evolution of number of site works per month
def get_plot_count_chant():

    def get_count_mensuel(df):
        df = df.copy()
        years = ['2021','2022','2023']
        mois = ['janvier','fevrier','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre']
        df_result = pd.DataFrame()
        for year in years :
            get_ser = df.set_index(['debut_chan']).sort_index().loc[year,'id_chantie'].resample('M').agg('count')
            list_count = get_ser.to_list()
            get_col = pd.DataFrame(index=mois,data=list_count,columns=[year])
            df_result = pd.concat([df_result,get_col],axis=1)
        # integrate mean to dataframe
        col_mean = df_result.mean(axis=1)
        df_result = pd.concat([df_result,col_mean],axis=1)
        df_result = df_result.rename(columns={0:'mean'})
        return df_result
    
    def get_plot_lines(df):
        df = df.copy()
        df = df.stack().reset_index().rename(columns={'level_0':'month','level_1':'year',0:'count'})
        fig = px.line(df,x='month',y='count',color='year',template='plotly_white')
        fig.for_each_trace(
            lambda trace: trace.update(line=dict(dash='dash',color='black')) if trace.name == "mean" else (),    
        )
        return fig
    
    # load data
    df = load_chantiers()
    # format dataset
    df = format_dataset(df,del_history=False)
    # get dataset fixed
    df = get_fix_data(df,del_history=False)
    chant_mensuel = get_count_mensuel(df)
    fig = get_plot_lines(chant_mensuel)
    return fig