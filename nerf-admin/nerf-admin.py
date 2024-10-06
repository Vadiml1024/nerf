import streamlit as st
import mysql.connector
from mysql.connector import Error
import pandas as pd
from datetime import datetime

# Database connection function
def create_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='nerfbot_db',
            user='root',
            password='rootpass'  # Replace with your actual password
        )
        return connection
    except Error as e:
        st.error(f"Error connecting to MySQL Database: {e}")
        return None

# Function to execute SQL queries
def execute_query(connection, query, params=None):
    cursor = connection.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        connection.commit()
        return cursor
    except Error as e:
        st.error(f"Error executing query: {e}")
        return None

# Function to fetch all rows from a table
def get_all_rows(connection, table_name):
    query = f"SELECT * FROM {table_name}"
    cursor = execute_query(connection, query)
    if cursor:
        return cursor.fetchall()
    return []

# Function to search row by id
def search_row(connection, table_name, id_column, id_value):
    query = f"SELECT * FROM {table_name} WHERE {id_column} = %s"
    cursor = execute_query(connection, query, (id_value,))
    if cursor:
        return cursor.fetchone()
    return None

# Function to update row
def update_row(connection, table_name, id_column, id_value, column_values):
    set_clause = ", ".join([f"{col} = %s" for col in column_values.keys()])
    query = f"UPDATE {table_name} SET {set_clause} WHERE {id_column} = %s"
    values = list(column_values.values()) + [id_value]
    execute_query(connection, query, values)

# Function to delete row
def delete_row(connection, table_name, id_column, id_value):
    query = f"DELETE FROM {table_name} WHERE {id_column} = %s"
    execute_query(connection, query, (id_value,))

# Function to insert new row
def insert_row(connection, table_name, column_values):
    columns = ", ".join(column_values.keys())
    placeholders = ", ".join(["%s"] * len(column_values))
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
    execute_query(connection, query, list(column_values.values()))

# Streamlit app
def main():
    st.title("NerfBot Database Management")

    # Create database connection
    connection = create_connection()
    if not connection:
        return

    # Sidebar for navigation
    table = st.sidebar.selectbox("Choose a table", ["subscribers", "subscription_levels", "system_config"])
    action = st.sidebar.selectbox("Choose an action", ["View", "Search", "Update", "Delete", "Insert"])

    if table == "subscribers":
        id_column = "user_id"
        columns = ["User ID", "ID", "Subscription Level", "Current Credits", "Subscription Anniversary", "Last Reset Date"]
    elif table == "subscription_levels":
        id_column = "subscription_level"
        columns = ["Subscription Level", "Max Credits Per Day", "Credits Per Shot"]
    else:  # system_config
        id_column = "config_key"
        columns = ["Config Key", "Config Value"]

    if action == "View":
        st.header(f"All {table.capitalize()}")
        rows = get_all_rows(connection, table)
        if rows:
            df = pd.DataFrame(rows, columns=columns)
            st.dataframe(df)
        else:
            st.info(f"No {table} found.")

    elif action == "Search":
        st.header(f"Search {table.capitalize()}")
        search_value = st.text_input(f"Enter {id_column}")
        if st.button("Search"):
            row = search_row(connection, table, id_column, search_value)
            if row:
                st.success(f"{table.capitalize()} found!")
                st.write(pd.DataFrame([row], columns=columns))
            else:
                st.warning(f"{table.capitalize()} not found.")

    elif action == "Update":
        st.header(f"Update {table.capitalize()}")
        search_value = st.text_input(f"Enter {id_column} to update")
        if st.button("Search for Update"):
            row = search_row(connection, table, id_column, search_value)
            if row:
                st.success(f"{table.capitalize()} found! Update the fields below:")
                new_values = {}
                for i, col in enumerate(columns):
                    if col.lower() != id_column.lower() and col.lower() != 'id':
                        if 'date' in col.lower():
                            new_values[col] = st.date_input(f"New {col}", value=row[i])
                        elif 'level' in col.lower() or 'credits' in col.lower():
                            new_values[col] = st.number_input(f"New {col}", value=row[i], min_value=0)
                        else:
                            new_values[col] = st.text_input(f"New {col}", value=row[i])
                if st.button("Update"):
                    update_row(connection, table, id_column, search_value, new_values)
                    st.success(f"{table.capitalize()} updated successfully!")
            else:
                st.warning(f"{table.capitalize()} not found.")

    elif action == "Delete":
        st.header(f"Delete {table.capitalize()}")
        delete_value = st.text_input(f"Enter {id_column} to delete")
        if st.button("Search for Deletion"):
            row = search_row(connection, table, id_column, delete_value)
            if row:
                st.warning(f"{table.capitalize()} found. Are you sure you want to delete?")
                st.write(pd.DataFrame([row], columns=columns))
                if st.button("Confirm Deletion"):
                    delete_row(connection, table, id_column, delete_value)
                    st.success(f"{table.capitalize()} deleted successfully!")
            else:
                st.warning(f"{table.capitalize()} not found.")

    elif action == "Insert":
        st.header(f"Insert New {table.capitalize()}")
        new_values = {}
        for col in columns:
            if col.lower() != 'id':
                if 'date' in col.lower():
                    new_values[col] = st.date_input(f"{col}")
                elif 'level' in col.lower() or 'credits' in col.lower():
                    new_values[col] = st.number_input(f"{col}", min_value=0)
                else:
                    new_values[col] = st.text_input(f"{col}")
        if st.button("Insert"):
            insert_row(connection, table, new_values)
            st.success(f"New {table.capitalize()} inserted successfully!")

    # Close the database connection
    if connection.is_connected():
        connection.close()

if __name__ == "__main__":
    main()

