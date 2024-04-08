import datetime
import pandas as pd
import os
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title='Streamlit App', layout='wide')

# Create a connection object.
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.warning('Failed to connect to the spreadsheet')

def retrieve_worksheet_data(worksheet, col_range, reference_col):
    # get data from the spreadsheet
    df = conn.read(worksheet=worksheet,
                   ttl='10m',
                   index_col=False,
                   usecols = list(range(col_range))
                   )

    df = remove_nan_rows(df, reference_col)
    return df

def remove_nan_rows(df, reference_col):
    # remove rows containing nan in a reference col
    df = df.dropna(subset=[reference_col])
    return df

def remove_missing_value(df):
    return df.fillna(0)

def insert_col(df: pd.DataFrame , col_name: str, position: int, val):
    if col_name not in df.columns:
        df.insert(position, col_name, val)
    return df

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
    s['selected'] = s['selected'].astype(bool)

    # concat the new entry to the DataFrame in session state
    st.session_state.df = pd.concat([st.session_state.df, s])

def add_to_wanted_list(time, crime, total_fine):
    new_entry = {
        'selected': False,
        'ID/Name': '',
        '指名手配開始時刻':time.strftime('%Y/%m/%d %H:%M'),
        '指名手配解除時刻': (time + datetime.timedelta(hours=st.session_state['指名手配時間'])).strftime('%Y/%m/%d %H:%M'),
        '罪状': crime,
        '罰金額': total_fine
    }
    s = pd.Series(new_entry).to_frame().T
    s['selected'] = s['selected'].astype(bool)

    # concat the new entry to the DataFrame in session state
    st.session_state.df_wanted = pd.concat([st.session_state.df_wanted, s])

def update_gspreadsheet(data, worksheet_name):

    df = conn.update(
        worksheet=worksheet_name,
        data=data
    )
    st.cache_data.clear()

    return df
# worksheet name
worksheet_name_crime = 'Crime_Fine_list'
worksheet_name_wanted = 'Wanted_list'

df = retrieve_worksheet_data(worksheet_name_crime, 3, 'crime_id')

df_wanted = retrieve_worksheet_data(worksheet_name_wanted,5,'ID/Name')
df_wanted = insert_col(df_wanted, 'selected', 0, False)

df['fine']=df['fine'].pipe(remove_missing_value)\
    .pipe(change_fine_dtype)

# preparing check boxes for the dataframe
df['selected'] = [False for i in range(df.shape[0])]

list_crime = df['crime'].sort_values().unique().tolist()

# title
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

        if st.button('指名手配に追加'):
            #japan time (utc + 9 hours)
            jst_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))

            add_to_wanted_list(
                jst_time,
                st.session_state.df.crime.unique().tolist(),
                st.session_state.df.fine.sum()
                )

        st.session_state['指名手配時間'] = 72
        if st.toggle('指名手配時間の変更'):
            duration = st.number_input('指名手配時間(時間)',value=72)
            if duration != st.session_state['指名手配時間']:
                st.session_state['指名手配時間'] = duration
            else:
                pass


    st.divider()
    st.header('指名手配者')

    if 'df_wanted' not in st.session_state:
        st.session_state.df_wanted = df_wanted

    st.session_state.df_wanted = st.data_editor(st.session_state.df_wanted,
                                                column_config = {
                                                    'selected': st.column_config.CheckboxColumn('selected', default = False)},
                                                hide_index = True,
                                                use_container_width=True)

    bs = st.columns(4)
    with bs[0]:
        if st.button('Delete selected',key='指名手配リスト_del'):
            st.session_state.df_wanted = st.session_state.df_wanted[st.session_state.df_wanted['selected'] == False]
            st.success('Data deleted.')
    with bs[1]:
        # tested ok
        if st.button('Delete all',key='指名手配リスト_del_all'):
            cols = st.session_state.df_wanted.columns
            _df = pd.DataFrame(columns = cols)
            conn.clear(worksheet=worksheet_name_wanted)
            df_wanted = update_gspreadsheet(_df, worksheet_name_wanted)
            # df_wanted = conn.update(
            #     worksheet=worksheet_name_wanted,
            #     data=_df
            # )
            # st.cache_data.clear()
            df_wanted = insert_col(df_wanted, 'selected', 0, False)
            st.session_state.df_wanted = df_wanted
            st.success('Data deleted.')
            st.rerun()
    with bs[2]:
        if st.button('手配リスト更新',key='指名手配リスト_update'):
            st.rerun()

    with bs[3]:
        if st.button('変更を保存'):
            df_data = pd.DataFrame(st.session_state.df_wanted.iloc[:,1:])
            st.dataframe(df_data)

            df_wanted = conn.update(
            worksheet=worksheet_name_wanted,
            data=df_data
        )
            st.cache_data.clear()
            st.toast('リストが更新されました')
            st.rerun()

# ID/Name
# 指名手配開始時刻
# 指名手配解除時刻
# 罪状
# 罰金額

# if st.button('Delete all',key='指名手配リスト_del_all_test'):

