from functions import *
from filter_df import *

# from secret import *
# use_proxy(on=True)

 ################# CONFIG APP
st.set_page_config(page_title='Chantiers 3M', page_icon=None, layout="wide", initial_sidebar_state="auto", menu_items=None)

################## CONFIG MENU
with st.sidebar:
    selected = option_menu(
        menu_title="Main Menu",
        options=['Data Explorer','Data Controller','History Analysis','Activity'],
        default_index=1

    )

################# LOAD AND PREPARE DATASETS
# load data
gdf = load_dataset(data='hybrid', historic_deleted='living')

# get dataset fixed
gdf_fix = get_fix_data(gdf)

#################################
###### PAGE DATA EXPLORER   #####
#################################

if selected == 'Data Explorer':
    data_option = st.selectbox(
        'Choix du dataset à explorer ?',
        ('Chantiers cloturés', 'Chantiers vivants', 'Chantiers à analyser'), index=2
    )

    if data_option == 'Chantiers à analyser':
        dataset = load_dataset(data='hybrid', historic_deleted='unliving')

    elif data_option == 'Chantiers cloturés':
        dataset = load_dataset(data='historic', historic_deleted='living')

    elif data_option == 'Chantiers vivants':
        dataset = load_dataset(data='current', historic_deleted='living')
    else : dataset = None

    # manage geometry because not display with st.dataframe
    col_to_keep = dataset.columns[dataset.dtypes !='geometry']
    dataset = dataset[col_to_keep]
    # control display of date format 
    table = st.data_editor(filter_dataframe(dataset),
                   hide_index=True,
                   column_config={
                        "debut_chan": st.column_config.DateColumn(
                            "Début Chantier",
                            # min_value=date(1900, 1, 1),
                            # max_value=date(2005, 1, 1),
                            format="DD.MM.YYYY",
                            step=1,
                        ),
                        "fin_chanti":st.column_config.DateColumn(
                            "Fin chantier",
                            format="DD.MM.YYYY",
                            step=1
                        )
                    },)
    st.sidebar.metric(label="Total Ligne", value=len(table),delta=len(dataset))

#################################
###### PAGE DATA CONTROLLER #####
#################################

if selected == 'Data Controller':

    # get controllers
    controllers = get_controllers(gdf)

    ###### CONTENERS ###########
    col1,col2 = st.columns([0.75,0.25])
    with col1:
        st.write('# Suivi de la qualité des données')
    with col2:
        st.metric("Chantiers scannés",value=gdf.shape[0])
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Ouverts / Terminés", value=controllers.loc['open_expired'])
    with col2:
        st.metric("En instruction / Terminés", value=controllers.loc['instruction_expired'])
    with col3:
        st.metric("En instruction / En cours", value=controllers.loc['instruction_current'])
    with col4:
        st.metric("Période négative", value=controllers.loc['negative_period'])
    st.markdown("---")
    st.plotly_chart(controllers_by_pole(gdf),use_container_width=True)

if selected == 'Activity':

    ###################################
    ####### PAGE ANALYSIS   ###########
    ###################################

    indicators = get_indicators(gdf_fix)

    ############### TITRE
    st.markdown("<center><h1>Chantiers sur la métropole de Montpellier</center>",unsafe_allow_html=True)
    st.divider()

    ############### INDICATORS
    col1,col2,col3,col4 = st.columns(4)
    with col1:
        st.metric('Chantiers ouverts', value=indicators['open'])
    with col4:
        st.metric('Chantiers en instruction', value=indicators['inst'])

############### MAP 1
    radio = st.radio(label='choice',options=["Chantiers ouverts","Chantiers en instruction"], horizontal=True, label_visibility='hidden')
    if radio =='Chantiers ouverts':
        # call function for get chantier by sectors    
        chant_by_sect = get_chant_by_sectors(gdf_fix.query("etape=='Ouvert'"))
    else:
        chant_by_sect = get_chant_by_sectors(gdf_fix.query("etape!='Ouvert'"))
    # call function to get map
    map = get_map(chant_by_sect)
    # call function to get sunburst
    fig_sunb = get_sunb(chant_by_sect)
    # prepare columns
    col1, col2 = st.columns(2) 
    with col1:
        # display map
        map_display = st.plotly_chart(map)
    with col2:
        # display sunburst
        sunb_display = st.plotly_chart(fig_sunb)

