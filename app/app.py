import datetime
import pandas as pd
import os
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import time

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

    try:
        crime_id = df['crime_id'][df['crime'] == crime].values[0]
    except IndexError:
        st.warning('罪状はコンマ(,)、半角スペース( )、もしくは点(、)で区切ってください')
        st.stop()

    crime = df['crime'][df['crime'] == crime].values[0]
    fine = df['fine'][df['crime'] == crime].values[0]
    return sel, crime_id, crime, fine

def add_crime_to_dataframe(sel, crime_id, crime, fine):
    new_entry = {
        'selected': sel,
        '罪状ID': crime_id,
        '罪状': crime,
        '罰金額': int(fine),
    }
    s = pd.Series(new_entry).to_frame().T
    s['selected'] = s['selected'].astype(bool)

    # concat the new entry to the DataFrame in session state
    st.session_state.df_new_registry = pd.concat([st.session_state.df_new_registry, s])

def add_to_wanted_list(time, crime, total_fine):
    new_entry = {
        'selected': False,
        'ID/Name': '',
        '指名手配開始時刻':time.strftime('%Y/%m/%d %H:%M'),
        '指名手配解除時刻': (time + datetime.timedelta(hours=st.session_state['指名手配時間'])).strftime('%Y/%m/%d %H:%M'),
        '罪状': clear_character(str(crime)),
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

    df = insert_col(df, 'selected', 0, False)

    return df

def clear_character(text: str):
    chars = "[]'"
    for c in chars:
        text = text.replace(c, '')
    return text

def create_preset_key_vals(df: pd.DataFrame):
    # make a preset key and val pair from spreadsheet
    dict = {}

    rows = df.shape[0]
    for row in range(rows):
        idx = df['プリセット名'][row]
        vals = df['罪状リスト'].values[row]
        if ',' in vals:
            vals = [val.split() for val in vals.split(',')]
            # flatten list of lists
            vals = [x for val in vals for x in val]
        elif '、' in vals:
            vals = [val.split() for val in vals.split('、')]
            vals = [x for val in vals for x in val]
        else:
            vals = vals.split()


        dict[idx] = vals

    return dict

def create_preset_button(df: pd.DataFrame):
    # create a preset button from a preset key and val pair

    dict = create_preset_key_vals(df)

    for key, val in dict.items():
        if st.button(key, key=key):
            preset_items = val
            for item in preset_items:
                if item not in st.session_state.df_new_registry['罪状'].tolist():
                    sel, crime_id, crime, fine = get_crime_data(st.session_state.df_crime, str(item))
                    add_crime_to_dataframe(sel, crime_id, crime, fine)
                else:
                    pass

# worksheet name
worksheet_name_crime = '罪状及び罰金一覧'
worksheet_name_wanted = '指名手配者リスト'

if 'df_crime' not in st.session_state:
    df_crime = retrieve_worksheet_data(worksheet_name_crime, 3, 'crime_id')
    df_crime['fine']=df_crime['fine'].pipe(remove_missing_value)\
        .pipe(change_fine_dtype)
    st.session_state.df_crime = df_crime

df_wanted = retrieve_worksheet_data(worksheet_name_wanted,5,'ID/Name')
df_wanted = insert_col(df_wanted, 'selected', 0, False)

if 'df_wanted' not in st.session_state:
    st.session_state.df_wanted = df_wanted

cols_new_registry = ['selected', '罪状ID','罪状','罰金額']
df_new_registry = pd.DataFrame(columns=cols_new_registry)
df_new_registry['selected'] = df_new_registry['selected'].astype(bool)

if 'df_new_registry' not in st.session_state:
    st.session_state.df_new_registry = df_new_registry


# title
st.header('ストグラ警察業務 罰金計算機')
st.divider()

# create page columns
a1,a2,a3 = st.columns([.75,.25,2])

# first column's content
with a1:
    st.subheader('罪状を追加')

    # selecting crime to add
    crime_list = st.session_state.df_crime['crime'].sort_values().unique().tolist()
    crime = st.selectbox('Select crime:', crime_list)

    sel, crime_id, crime, fine = get_crime_data(st.session_state.df_crime, crime)

    # preparing a button that records/appends the user input to the list/dataframe
    if st.button('リストに追加'):
        #  check dupliation
        if crime not in st.session_state.df_new_registry['罪状'].tolist():

            # concat the new entry to the DataFrame in session state
            add_crime_to_dataframe(sel, crime_id, crime, fine)

            # pops a small notification on below-right
            st.toast('リストに追加されました')
        else:
            # duplication warning
            st.warning('すでに登録されています')

    st.info('各大型もしくは大型犯罪でよく使われる罪状をまとめて登録することができます')
    worksheet_name_preset = 'プリセット'
    df_preset = retrieve_worksheet_data(worksheet_name_preset, 2, 'プリセット名')
    # toggle button
    if st.toggle('犯罪用プリセット'):

        create_preset_button(df_preset)

with a3:
    st.subheader('現在追加されている罪状リスト')
    st.session_state.df_new_registry = st.data_editor(st.session_state.df_new_registry,
                                                      column_config = {
                                                          'selected': st.column_config.CheckboxColumn('selected', default = False)
                                                          },
                                                      hide_index = True,
                                                      use_container_width=True
                                                      )
    b1,b2,b3 = st.columns([1,1.5,1.5])
    with b1:
        if st.button('Delete selected'):
            st.session_state.df_new_registry = st.session_state.df_new_registry[st.session_state.df_new_registry['selected'] == False]
            st.success('Data deleted.')
    with b2:
        if st.button('Delete all'):
            cols = st.session_state.df_new_registry.columns
            st.session_state.df_new_registry = pd.DataFrame(columns = cols)
            st.success('Data deleted.')
    with b3:
        sum_fine = st.session_state.df_new_registry['罰金額'].sum()
        st.markdown(f'<b>罰金総額 :</b> ${sum_fine} ドル', unsafe_allow_html=True)

        if st.button('指名手配に追加'):
            #japan time (utc + 9 hours)
            jst_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
            # st.write(st.session_state.df_new_registry['罪状'].unique().tolist())
            crimes = clear_character(str(st.session_state.df_new_registry['罪状'].unique().tolist()))

            add_to_wanted_list(jst_time,crimes,sum_fine)

        st.session_state['指名手配時間'] = 72
        if st.toggle('指名手配時間の変更'):
            duration = st.number_input('指名手配時間 (時間)',value=72)
            if duration != st.session_state['指名手配時間']:
                st.session_state['指名手配時間'] = duration
            else:
                pass

    st.divider()
    st.header('指名手配者')

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
            time.sleep(1)
            st.rerun()
    with bs[1]:
        if st.button('Delete all',key='指名手配リスト_del_all'):
            cols = st.session_state.df_wanted.columns
            # clear all data in worksheet (overwrite the dataframe with empty data)
            st.session_state.df_wanted = pd.DataFrame(columns = cols)
            st.success('Data deleted.')
            time.sleep(1)
            st.rerun()

    st.info('指名手配者リストの追加/変更は下記のいずれかのボタンが押されるまでスプレッドに反映されません')
    cs = st.columns(4)
    with cs[0]:
        if 'warning' not in st.session_state:
            st.session_state.warning = False
        if st.button('手配リスト更新',key='指名手配リスト_update'):
            st.session_state.warning = True

    with cs[1]:
        if st.button('変更を保存'):
            data = st.session_state.df_wanted.drop('selected', axis=1)
            df_wanted = update_gspreadsheet(data, worksheet_name_wanted)
            st.session_state.df_wanted = df_wanted
            st.cache_data.clear()
            st.toast('リストが更新されました')
            time.sleep(1)
            st.rerun()

    if st.session_state.warning:
        st.warning('追加/変更を保存せず指名手配者リストの再読み込みを行います')

        cols = st.columns(2)
        with cols[0]:
            if st.button('手配リストの再読み込みをする', key='confirmation'):
                if (st.session_state.warning):
                    del st.session_state.df_wanted
                    _df = retrieve_worksheet_data(worksheet_name_wanted,5,'ID/Name')
                    _df = insert_col(df_wanted, 'selected', 0, False)
                    st.session_state.df_wanted = _df
                    st.cache_data.clear()

                    st.session_state.warning = False

                    st.rerun()

        with cols[1]:
            reject = st.button('手配リストの再読み込みをしない',key='reject')
            if reject:
                st.session_state.warning = False

