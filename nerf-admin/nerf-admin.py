
import streamlit as st
import mysql.connector
from mysql.connector import Error
import pandas as pd
from datetime import datetime, timedelta

# Initialize connection.
# Uses st.cache_resource to only run once.
@st.cache_resource
def init_connection():
    try:
        return mysql.connector.connect(
            host='localhost',  # Change this to your Docker container's IP if needed
            port=3306,  # Specify the port if it's not the default
            database='nerfbot_db',
            user='root',
            password='rootpass'
#            auth_plugin='mysql_native_password'
        )
    except Error as e:
        st.error(f"Error connecting to MySQL Database: {e}")
        return None

# Perform query.
# Uses st.cache_data to only rerun when the query changes or after 10 min.
#st.cache_data(ttl=600)
def run_query(query, params=None):
    conn = init_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor() as cur:
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            return cur.fetchall()
    except Error as e:
        st.error(f"Error executing query: {e}")
        return None


def execute_and_commit(query, params=None):
    conn = init_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
        conn.commit()
        return True
    except Error as e:
        st.error(f"Error executing query: {e}")
        conn.rollback()
        return False



def get_all_rows(table_name):
    query = f"SELECT * FROM {table_name}"
    return run_query(query)

def search_row(table_name, id_column, id_value):
    query = f"SELECT * FROM {table_name} WHERE {id_column} = %s"
    result = run_query(query, (id_value,))
    return result[0] if result else None

def update_row(table_name, id_column, id_value, column_values):
    set_clause = ", ".join([f"{col} = %s" for col in column_values.keys()])
    query = f"UPDATE {table_name} SET {set_clause} WHERE {id_column} = %s"
    values = list(column_values.values()) + [id_value]
    return execute_and_commit(query, values)

def delete_row(table_name, id_column, id_value):
    print("Enter delete-row\n")
    conn = init_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            print("In delete-row\n")
            query = f"DELETE FROM {table_name} WHERE {id_column} = %s"
            cur.execute(query, (id_value,))
            conn.commit()
            print("After commit\n")
        return cur.rowcount > 0  # Check if any row was actually deleted
    except Error as e:
        st.error(f"Error deleting row: {e}")
        conn.rollback()
        return False
    finally:
        if conn.is_connected():
            conn.close()

def insert_row(table_name, column_values):
    columns = ", ".join(column_values.keys())
    placeholders = ", ".join(["%s"] * len(column_values))
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
    return execute_and_commit(query, list(column_values.values()))

def main():
    st.title("NerfBot Database Management")

    # Sidebar for navigation
    table = st.sidebar.selectbox("Choose a table", ["subscribers", "subscription_levels", "system_config"])
    action = st.sidebar.selectbox("Choose an action", ["View", "Search", "Update", "Delete", "Insert"])

    if table == "subscribers":
        id_column = "user_id"
        columns = ["user_id", "id", "subscription_level", "current_credits", "subscription_anniversary", "last_reset_date"]
        display_columns = ["User ID", "ID", "Subscription Level", "Current Credits", "Subscription Anniversary", "Last Reset Date"]
        date_columns = ["subscription_anniversary", "last_reset_date"]
    elif table == "subscription_levels":
        id_column = "subscription_level"
        columns = ["subscription_level", "max_credits_per_day", "credits_per_shot"]
        display_columns = ["Subscription Level", "Max Credits Per Day", "Credits Per Shot"]
        date_columns = []
    else:  # system_config
        id_column = "config_key"
        columns = ["config_key", "config_value"]
        display_columns = ["Config Key", "Config Value"]
        date_columns = []

    if action == "View":
        st.header(f"All {table.capitalize()}")
        rows = get_all_rows(table)
        if rows:
            df = pd.DataFrame(rows, columns=columns)
            df.columns = display_columns  # Set display column names
            st.dataframe(df)
        else:
            st.info(f"No {table} found.")

    elif action == "Search":
        st.header(f"Search {table.capitalize()}")
        search_value = st.text_input(f"Enter {id_column}")
        if st.button("Search"):
            row = search_row(table, id_column, search_value)
            if row:
                st.success(f"{table.capitalize()} found!")
                df = pd.DataFrame([row], columns=columns)
                df.columns = display_columns  # Set display column names
                st.write(df)
            else:
                st.warning(f"{table.capitalize()} not found.")

    elif action == "Update":
        st.header(f"Update {table.capitalize()}")
        
        if 'update_stage' not in st.session_state:
            st.session_state.update_stage = 'search'
        
        if 'search_value' not in st.session_state:
            st.session_state.search_value = ''
        
        search_value = st.text_input(f"Enter {id_column} to update", value=st.session_state.search_value)
        
        if st.button("Search for Update") or st.session_state.update_stage == 'edit':
            row = search_row(table, id_column, search_value)
            if row:
                st.session_state.update_row = row
                st.session_state.update_stage = 'edit'
                st.session_state.search_value = search_value
            else:
                st.warning(f"{table.capitalize()} not found.")
                st.session_state.update_stage = 'search'
        
        if st.session_state.update_stage == 'edit':
            st.success(f"{table.capitalize()} found! Update the fields below:")
            row = st.session_state.update_row
            new_values = {}
            for i, col in enumerate(columns):
                if col != id_column and col != 'id':
                    if col in date_columns:
                        new_values[col] = st.date_input(f"New {display_columns[i]}", value=row[i])
                    elif 'level' in col or 'credits' in col:
                        new_values[col] = st.number_input(f"New {display_columns[i]}", value=row[i], min_value=0)
                    else:
                        new_values[col] = st.text_input(f"New {display_columns[i]}", value=row[i])
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Confirm Update"):
                    if update_row(table, id_column, row[columns.index(id_column)], new_values):
                        st.success(f"{table.capitalize()} updated successfully!")
                        st.session_state.update_stage = 'search'
                        st.session_state.search_value = ''
                    else:
                        st.error(f"Failed to update {table}.")
            
            with col2:
                if st.button("Cancel Update"):
                    st.session_state.update_stage = 'search'
                    st.session_state.search_value = ''

    elif action == "Insert":
        st.header(f"Insert New {table.capitalize()}")
        new_values = {}
        for i, col in enumerate(columns):
            if col != 'id':
                if col == 'subscription_anniversary':
                    default_anniversary = (datetime.now() + timedelta(days=30)).date()
                    new_values[col] = st.date_input(f"{display_columns[i]} (default: 30 days from today)", value=default_anniversary)
                elif col == 'last_reset_date':
                    default_reset = datetime.now().date()
                    new_values[col] = st.date_input(f"{display_columns[i]} (default: today)", value=default_reset)
                elif col in date_columns:
                    new_values[col] = st.date_input(f"{display_columns[i]}")
                elif 'level' in col or 'credits' in col:
                    new_values[col] = st.number_input(f"{display_columns[i]}", min_value=0)
                else:
                    new_values[col] = st.text_input(f"{display_columns[i]}")
        if st.button("Insert"):
            if insert_row(table, new_values):
                st.success(f"New {table.capitalize()} inserted successfully!")
            else:
                st.error(f"Failed to insert new {table}.")

if __name__ == "__main__":
    main()