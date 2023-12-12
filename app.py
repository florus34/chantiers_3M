from functions import *
# from secret import *
# use_proxy(on=True)

################# CONFIG APP
st.set_page_config(page_title='Chantiers 3M', page_icon=None, layout="wide", initial_sidebar_state="auto", menu_items=None)

# load data
data = load_chantiers()

# format dataset
gdf = format_dataset(data)

# get dataset fixed
gdf_fix = get_fix_data(gdf)

# get indicators
indicators = get_indicators(gdf_fix)



################# SESSION STATE
if 'summarize_controllers' not in st.session_state:
    st.session_state['summarize_controllers'] = get_controllers(gdf_fix)


###### SIDEBAR CONTROLE DATA ########
def display_callback():
    if st.session_state['toggle_k'] == True:
        st.session_state['summarize_controllers'] = get_controllers(gdf_fix)
    else :
        st.session_state['summarize_controllers'] = get_controllers(gdf)

st.sidebar.write('# Contrôle données')
st.sidebar.write(st.session_state['summarize_controllers'])

fix_data_toggle = st.sidebar.toggle(label='Données corrigées', on_change=display_callback, key='toggle_k',value=True)

###################################
####### CENTRAL DISPLAY ###########
###################################

############### TITRE
st.markdown("<center><h1>Chantiers sur la métropole de Montpellier</center>",unsafe_allow_html=True)
st.divider()

############### INDICATORS
if st.session_state['toggle_k'] == True:
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

