import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.style as style
import requests
from datetime import datetime, timedelta

## Global constants and variables
RED = "#D72827"
BLUE = "#1F77B4"
GREEN = "#2AA12B"
ORANGE = "#FF7F0F"

SA_URL = 'https://services.arcgis.com/g1fRTDLeMgspWrYp/arcgis/rest/services/vDateCOVID19_Tracker_Public/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=json'

state_pops = pd.read_csv('states.csv', index_col=0)

## Create dict for chart menu options
chart_dict = {
    "Reported Cases": ("Reported Cases", "ReportedCum", "ReportedOn", "Reported7dMA"),
    "Mortality": ("Mortality Information", "DeathsCum", "Deceased", "Deceased7dMA"),
    "Testing Information": ("Cumulative and Daily Testing Information", None),
    "Recoveries": ("Cumulative and Daily Changes in Recovery / Still Ill", "Recovered", "Recovered_Daily_Change", "StillIll"),
    "ICU Information": ("COVID ICU Patients", "COVIDnICU"),
    "Ventilator Information": ("COVID Ventilator Patients", "COVIDonVent", "TotalVents", "AvailVent"),
    "Staffed Bed Availability": ("Staffed Bed Availability Information", "TotalStaffedBeds", "AvailStaffedBeds"),
    "Multiview": ("Multiview Chart"),
}

## Multiview chart options
multiview_options = {"Cumulative Reported Cases": "ReportedCum",
                "Daily Reported Cases": "ReportedOn",
                "Reported Cases 7d Moving Avg": "Reported7dMA",
                "Cumulative Mortality": "DeathsCum",
                "Daily Mortality": "Deceased",
                "Daily Mortality 7d Moving Avg": "Deceased7dMA",
                "Cumulative Recoveries": "Recovered",
                "Daily Change in Recoveries": "Recovered_Daily_Change",
                "Still Ill Patients": "StillIll",
                "Daily COVID ICU Census": "COVIDnICU",
                "Daily COVID Ventilator Census":"COVIDonVent",
                "Daily Positive Tests": "DBCTestPositive",
                "Daily Positive Tests 7d Moving Avg": "DBCTestPositive7dMA"
}

state_graph_types = ['positive', 'positive_per100k', 'death', 'death_per100k']

def format_func(value, tick=None):
    if abs(value) < 1000:
        num_thousands = 0
    else:
        num_thousands = 1
    value = round(value / 1000**num_thousands, 2)
    return f'{value:g}'+' K'[num_thousands]

def fetch_san_antonio():
    ## Retrieve json data
    r = requests.get(SA_URL)
    raw_json = r.json()

    ## Parse json data
    input_rows = []
    for row in raw_json['features']:
        input_rows.append(row['attributes'])

    ## Load into DataFrame
    df = pd.DataFrame(input_rows)

    # Set Date to index as datetime
    df['Date'] = pd.to_datetime(df['Date'], unit='ms')
    df.set_index('Date', inplace=True, drop=True)
    # Get rid of dates without data
    df = df[df.index.notnull()]

    ## Create additional columns
    # Daily change in recovered cases
    df["Recovered_Daily_Change"] = (df['Recovered'] - df['Recovered'].shift(1)).dropna()
    # Reported cases 7 day moving average
    df["Reported7dMA"] = df["ReportedOn"].rolling(7).mean()
    # Daily Mortality 7 day moving average
    df["Deceased7dMA"] = df["Deceased"].rolling(7).mean()
    # Daily Positive Cases 7 day moving average
    df["DBCTestPositive7dMA"] = df["DBCTestPositive"].rolling(7).mean()

    return df

df = fetch_san_antonio()

def fetch_states(states):
    state_dict = {}
    for state in states:
        population =state_pops.loc[state]['2018 Population']
        df = pd.read_json(f'https://covidtracking.com/api/v1/states/{state.lower()}/daily.json')
        df['date'] = pd.to_datetime(df['date'], format="%Y%m%d")
        df.set_index('date', inplace=True)
        df.sort_index(ascending=True, inplace=True)
        df['positive_7dMA'] = df['positive'].rolling(7).mean()
        df['death_7dMA'] = df['death'].rolling(7).mean()
        df['positive_per100k'] = df['positive']/population*100000
        df['death_per100k'] = df['death']/population*100000
        state_dict[state] = df
    return state_dict

def make_state_graphs(state_dict, state_graph_types):
    for graph_type in state_graph_types:
        for state, df in state_dict.items():
            df[graph_type].plot(label=state.upper())
        plt.legend([key.upper() for key in state_dict.keys()], loc='upper left')
        plt.show()

def make_chart(choice, start_date, end_date):
    if choice in ["Multiview"]:
        st.header("Multiview")
        st.subheader("This is a unique type of chart which allows overlay of multiple graphs.")
        multi_choice = st.multiselect("Select charts to display:",
                        options=list(multiview_options.keys()),
                        default=list(multiview_options.keys())[1:3])
        if len(multi_choice) > 0:
            ax = df[[multiview_options[x] for x in multi_choice] ].loc[start_date : end_date + timedelta(days=1)].plot(title="Multiview Chart")
            ax.legend(multi_choice)
            st.pyplot()
        else:
            st.subheader("Please select one or more charts to display.")

    elif choice in ["Testing Information"]:
        st.header(chart_dict[choice][0])
        df[df['BCLabTests'].notnull()]['BCLabTests'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label="Total Tests", title="Cumulative " + choice)
        df[df['BCTestNegative'].notnull()]['BCTestNegative'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label='Negative Tests')
        df[df['BCTestPositive'].notnull()]['BCTestPositive'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label='Positive Tests')
        plt.legend()
        st.pyplot()

        df[df['DBCLabTests'].notnull()]['DBCLabTests'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label="Total Tests", title="Daily " + choice)
        df[df['DBCTestNegative'].notnull()]['DBCTestNegative'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label='Negative Tests')
        df[df['DBCTestPositive'].notnull()]['DBCTestPositive'].loc[start_date : end_date + timedelta(days=1)].abs().plot(kind='area', label='Positive Tests')

        plt.legend()
        st.pyplot()

        df["DBCTestPositive7dMA"].loc[start_date : end_date + timedelta(days=1)].plot(label="Daily Positive Tests 7d Moving Avg", title="Reported Cases and Daily Postive Tests")
        df["Reported7dMA"].loc[start_date : end_date + timedelta(days=1)].plot(label= "Daily Reported Cases 7d Moving Avg")
        df[df['DBCTestPositive'].notnull()]['DBCTestPositive'].loc[start_date : end_date + timedelta(days=1)].abs().plot(kind='area', label='Daily Positive Tests', alpha=0.2)
        plt.legend()
        st.pyplot()

    elif choice in ["Reported Cases", "Mortality"]:
        st.header(chart_dict[choice][0])
        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()

        ax1.set_ylabel("Daily " + choice, c=BLUE)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(format_func))
        ax1.tick_params(axis='y', colors=BLUE)
        ax2.set_ylabel("Cumulative " + choice, c=RED, rotation=270, labelpad=10)
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(format_func))
        ax2.tick_params(axis='y', colors=RED)

        l1 = df[chart_dict[choice][1]].loc[start_date : end_date + timedelta(days=1)].plot(kind='line', ax=ax2, c=RED, title=f"Daily and Cumulative {choice} With 7dMA")
        l2 = df[chart_dict[choice][2]].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', ax=ax1, alpha=0.3, label='_nolegend_')
        l3 = df[chart_dict[choice][3]].loc[start_date : end_date + timedelta(days=1)].plot(kind='line', ax=ax1, c=ORANGE, label=f"Daily {choice} 7d Moving Avg")
        ax1.legend()
        st.pyplot()
    
    elif choice in ["Recoveries"]:
        st.header(chart_dict[choice][0])
        fig, ax1 = plt.subplots()
        df[chart_dict[choice][1]].loc[start_date : end_date + timedelta(days=1)].plot(label="Cumulative Recoveries", title="Recoveries")
        df[chart_dict[choice][2]].loc[start_date : end_date + timedelta(days=1)].plot(label="Daily Change in Recoveries")
        plt.legend()
        st.pyplot()
        df[chart_dict[choice][3]].loc[start_date : end_date + timedelta(days=1)].plot(title="Patients Who Are Still Ill", c=RED)
        st.pyplot()

    elif choice in ["ICU Information"]:
        st.header(chart_dict[choice][0])
        df[chart_dict[choice][1]].loc[start_date : end_date + timedelta(days=1)].plot(title=f"Daily COVID ICU Census")
        st.pyplot()

    elif choice in ["Ventilator Information"]:
        st.header(chart_dict[choice][0])
        df[chart_dict[choice][1]].loc[start_date : end_date + timedelta(days=1)].plot(title=f"Daily COVID Ventilator Census")
        st.pyplot()
        df[chart_dict[choice][2]].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label="Total Ventilators", title="Ventilator Availability")
        df[chart_dict[choice][3]].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label="Available Ventilators")
        plt.legend(loc=2)
        st.pyplot()

    elif choice in ["Staffed Bed Availability"]:
        st.header(chart_dict[choice][0])
        df[chart_dict[choice][1]].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label="Total Staffed Beds")
        df[chart_dict[choice][2]].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label="Available Staffed Beds")
        plt.legend(loc=2)
        st.pyplot()

def build_site():
    start_date = st.sidebar.date_input("Start Date", value=datetime(2020, 3, 19))
    end_date = st.sidebar.date_input("End Date", value=df.index.max())

    choices = st.sidebar.multiselect("Select individual charts to display:",
                            options=list(chart_dict.keys()),
                            default=list(chart_dict.keys())[:3])

    st.sidebar.markdown('### HELP:\n* Enter your start and stop dates.\n* Click in the box below the dates to select individual charts to display.\n'
                        '* __Multiview__ allows for viewing multiple graphs in one chart.\n'
                        '* Remember to scroll down to see all of the charts.')


    ## Render the main screen
    st.title("San Antonio COVID-19 Charts")
    st.markdown(f'The data for these charts were last updated on {str(df.index.max()).split()[0]}. '
                'See HELP in sidebar to the left.')
    st.markdown('')

    for choice in choices:
        make_chart(choice, start_date, end_date)

    st.subheader('Source:')
    st.code(SA_URL)

    if st.checkbox("See source data"):
        st.write("Source data:")
        st.dataframe(df)

    st.sidebar.markdown('&copy 2020, Lance Reinsmith')


if __name__ == "__main__":
    build_site()