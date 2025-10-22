import streamlit as st
import pandas as pd
from streamlit_app.db_helper import list_tables, table_count, sample_rows, get_conn, compute_plot_data

st.set_page_config(page_title='DV Petitions Explorer', layout='wide')

st.title('DV Petitions Explorer')

# Sidebar controls
st.sidebar.header('Controls')
path = st.sidebar.text_input('DB path', '../dv_petitions.db')

tables = list_tables(path)
selected = st.sidebar.selectbox('Table', tables)

# Pagination controls
st.sidebar.header('Preview options')
rows = st.sidebar.number_input('Rows per page', min_value=1, max_value=1000, value=50)
page = st.sidebar.number_input('Page', min_value=1, value=1)
offset = (page - 1) * rows

# Layout: two columns
left, right = st.columns([3, 1])

with left:
    st.header('Preview')
    try:
        df = pd.read_sql_query(f"SELECT * FROM {selected} LIMIT {rows} OFFSET {offset}", get_conn(path))
        st.dataframe(df)
        total = table_count(selected, path)
        st.caption(f'Page {page} — showing {len(df)} rows of {total} total')
    except Exception as e:
        st.error(f'Error loading table: {e}')

    # Plot area
    st.subheader('Plot')
    col = st.selectbox('Column', df.columns.tolist(), key='plot_col') if not df.empty else None
    topn = st.number_input('Top N', min_value=1, max_value=500, value=20)
    chart_type = st.selectbox('Chart type', ['bar', 'line', 'pie'])

    # compute_plot_data imported from db_helper

    if col and st.button('Plot'):
        labels, values = compute_plot_data(selected, col, topn, path)
        st.bar_chart(pd.Series(values, index=labels))
        # download buttons
        csv_data = 'label,value\n' + '\n'.join(f'{l},{v}' for l, v in zip(labels, values))
        st.download_button('Download plot CSV', csv_data, file_name='plot_data.csv')
        st.download_button('Download plot JSON', pd.Series(values, index=labels).to_json(), file_name='plot_data.json')

with right:
    st.header('Prebuilt queries')
    # Add a few useful prebuilt queries
    if st.button('Most common reasoning by state'):
        sql = """
SELECT p.state, r.reasoning, COUNT(*) as cnt
FROM Petitions p
JOIN Petition_Reasoning_Lookup pr ON p.petition_id = pr.petition_id
JOIN Reasoning r ON pr.reasoning_id = r.reasoning_id
GROUP BY p.state, r.reasoning
ORDER BY p.state, cnt DESC
LIMIT 500
"""
        try:
            dfq = pd.read_sql_query(sql, get_conn(path))
            st.dataframe(dfq)
            st.download_button('Download CSV', dfq.to_csv(index=False), file_name='reasoning_by_state.csv')
        except Exception as e:
            st.error(f'Query error: {e}')

    if st.button('Counts by result'):
        sql = "SELECT p.state, r.result, COUNT(*) as cnt FROM Petitions p JOIN Result r ON p.petition_id = r.petition_id GROUP BY p.state, r.result ORDER BY p.state, cnt DESC"
        try:
            dfq = pd.read_sql_query(sql, get_conn(path))
            st.dataframe(dfq)
            st.download_button('Download CSV', dfq.to_csv(index=False), file_name='counts_by_result.csv')
        except Exception as e:
            st.error(f'Query error: {e}')

    if st.button('Top petitioners (people)'):
        sql = "SELECT pe.name, COUNT(*) cnt FROM People pe JOIN Petition_People_Lookup ppl ON pe.person_id = ppl.person_id GROUP BY pe.name ORDER BY cnt DESC LIMIT 200"
        try:
            dfq = pd.read_sql_query(sql, get_conn(path))
            st.dataframe(dfq)
            st.download_button('Download CSV', dfq.to_csv(index=False), file_name='top_petitioners.csv')
        except Exception as e:
            st.error(f'Query error: {e}')
