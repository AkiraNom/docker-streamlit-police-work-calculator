import pandas as pd
import streamlit as st

st.set_page_config(page_title='Streamlit App', layout='wide')

def remove_missing_value(df):
    return df.fillna(0)

def change_fine_dtype(df):
    list_fine = []
    for item in df:
        if isinstance(item, int):
            list_fine.append(item)
        elif ',' in item:
            # print(f'{item}, {item.replace(",", "")}')
            list_fine.append(int(item.replace(',','')))
        elif '-' in item:
            list_fine.append(int(item.replace('-','0')))
        elif '' in item:
            list_fine.append(int(item.replace('','0')))
        else:
            pass

    return list_fine

def get_crime_data(df, crime):
    # setting up variables to fill in other columns for each entry (row)
    sel = False
    crime_id = df['crime_id'][df['crime'] == crime].values[0]
    crime = df['crime'][df['crime'] == crime].values[0]
    fine = df['fine'][df['crime'] == crime].values[0]

    return sel, crime_id, crime, fine

def add_crime_to_dataframe(sel, crime_id, crime, fine):
    new_entry = {
        'selected': sel,
        'crime_id': crime_id,
        'crime': crime,
        'fine': fine,
    }
    s = pd.Series(new_entry).to_frame().T

    # concat the new entry to the DataFrame in session state
    st.session_state.df = pd.concat([st.session_state.df, s])

df = pd.read_csv(r'app/data/test.csv')
df['fine']=df['fine'].pipe(remove_missing_value)\
    .pipe(change_fine_dtype)

# preparing check boxes for the dataframe
df['selected'] = [False for i in range(df.shape[0])]

list_crime = df['crime'].sort_values().unique().tolist()

# le title
st.header('ストグラ警察業務 罰金計算機')
st.divider()

# defining dataframe we want to dynamically interact with and make changes to within streamlit session.
# declared once at the beginning, like this:
if 'df' not in st.session_state:
        st.session_state.df = pd.DataFrame(columns = df.columns)
if 'full' not in st.session_state:
        st.session_state.full = df.copy()
# create page columns
a1,a2,a3 = st.columns([.75,.25,2])

# first column's content
with a1:
    st.subheader('罪状を追加')

    # selecting sub-category before scrolling through product names
    crime = st.selectbox('Select crime:', list_crime)

    sel, crime_id, crime, fine = get_crime_data(df, crime)

    # preparing a button that records/appends the user input to the list/dataframe
    if st.button('リストに追加'):
        if crime not in st.session_state.df['crime'].tolist():

            # concat the new entry to the DataFrame in session state
            add_crime_to_dataframe(sel, crime_id, crime, fine)

            # pops a small notification on below-right
            st.toast('リストに追加されました')
        else:
            # 重複回避
            st.warning('すでに登録されています')

    st.info('各大型もしくは大型犯罪でよく使われる罪状をまとめて登録することができます')
    # toggle button
    if st.toggle('犯罪用プリセット'):
        if st.button('客船'):
            preset_items = ['豪華客船強盗','PL殺人及び未遂']
            for item in preset_items:
                if item not in st.session_state.df['crime'].tolist():
                    sel, crime_id, crime, fine = get_crime_data(df, item)
                    add_crime_to_dataframe(sel, crime_id, crime, fine)
                else:
                    pass


with a3:
    st.subheader('現在追加されている罪状リスト')
    # not sure why session state is declared again here lol
    if 'df' not in st.session_state:
        st.session_state.df = df.copy()


    # to display the number of item in the list
    st.write('Num. of entry:', st.session_state.df.shape[0])
    st.session_state.df = st.data_editor(st.session_state.df.groupby(['selected','crime','crime_id']).agg({'fine':'sum'}).reset_index(),
    column_config = {
    'selected': st.column_config.CheckboxColumn('selected', default = False)
    }, hide_index = True, use_container_width=True)
    b1,b2,b3 = st.columns([1,1.5,1.5])
    with b1:
        if st.button('Delete selected'):
            st.session_state.df = st.session_state.df[st.session_state.df['selected'] == False]
            st.success('Data deleted.')
    with b2:
        if st.button('Delete all'):
            cols = st.session_state.df.columns
            st.session_state.df = pd.DataFrame(columns = cols)
            st.success('Data deleted.')
    with b3:
        st.markdown(f'<b>罰金総額 :</b> ${st.session_state.df.fine.sum()} ドル', unsafe_allow_html=True)
