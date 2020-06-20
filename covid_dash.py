import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

import requests
from datetime import datetime, timedelta

## Retrieve data
URL = 'https://services.arcgis.com/g1fRTDLeMgspWrYp/arcgis/rest/services/vDateCOVID19_Tracker_Public/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=json'
r = requests.get(URL)
raw_json = r.json()

## Parse data
input_rows = []
for row in raw_json['features']:
    input_rows.append(row['attributes'])

df = pd.DataFrame(input_rows)
df['Date'] = pd.to_datetime(df['Date'], unit='ms')
df.set_index('Date', inplace=True, drop=True)
df = df[df.index.notnull()]

## Create additional columns
for col in ['Recovered', 'Hospitalized']:
    df[col + "_Daily"] = (df[col] - df[col].shift(1)).dropna()

## Create dict for chart options
chart_dict = {
    "Multiview": ("Multiview Chart"),
    "Testing Information": ("Cumulative and Daily Testing Information", None, None),
    "Reported Cases": ("Cumulative and Daily Reported Cases", "ReportedCum", "ReportedOn"),
    "Mortality": ("Cumulative and Daily Mortality Information", "DeathsCum", "Deceased"),
    "Recoveries": ("Cumulative and Daily Recovery Information", "Recovered", "Recovered_Daily"),
    "Hospitalizations": ("Cumulative and Daily Hospitalization Information", "Hospitalized", "Hospitalized_Daily"),
    "COVID ICU Patients": ("Daily COVID ICU Patients", "COVIDnICU"),
    "COVID Ventilator Patients": ("Daily COVID Ventilator Patients", "COVIDonVent"),
    "Quarantine": ("Cumulative and Weekly Quarantine Information", "EverQuar", "WeekQuar"),
    "Ventilator Availability": ("Ventilator Availability Information", "TotalVents", "AvailVent", "Ventilators"),
    "Staffed Bed Availability": ("Staffed Bed Availability Information", "TotalStaffedBeds", "AvailStaffedBeds", "Staffed Beds")
}

## Sidebar
start_date = st.sidebar.date_input("Start Date", value=datetime(2020, 3, 19))
end_date = st.sidebar.date_input("End Date", value=df.index.max())

multi_options = {"Cumulative Reported Cases": "ReportedCum",
                "Daily Reported Cases": "ReportedOn",
                "Cumulative Mortality": "DeathsCum",
                "Daily Mortality": "Deceased",
                "Cumulative Recoveries": "Recovered",
                "Daily Recoveries": "Recovered_Daily",
                "Cumulative Hospitalizations": "Hospitalized",
                "Daily Hospitalizations": "Hospitalized_Daily",
                "Daily COVID ICU Patients": "COVIDnICU",
                "Daily COVID Ventilator Patients":"COVIDonVent"
}

choices = st.sidebar.multiselect("Select individual charts to display:",
                        options=list(chart_dict.keys()),
                        default=list(chart_dict.keys())[:2])

st.sidebar.markdown('### HELP:\n* Enter your start and stop dates.\n* Click the magnifying glass to select charts to display.  Or, type a keyword in the search bar.\n* Remember to scroll down to see all of the charts.')



## Render the main screen
st.title("San Antonio COVID-19 Charts")
st.subheader(f'The data for these charts were last updated at {df.index.max()}. Source:')
st.code(URL)

if st.checkbox("See source data"):
    st.write("Source data:")
    st.dataframe(df)

for choice in choices:
    if choice in ["Multiview"]:
        st.header("Multiview")
        multi_choice = st.multiselect("Select charts to display:",
                        options=list(multi_options.keys()),
                        default=list(multi_options.keys())[1])
        if len(multi_choice) > 0:
            ax = df[[multi_options[x] for x in multi_choice] ].loc[start_date : end_date + timedelta(days=1)].plot(title = "Multiview Chart")
            ax.legend(multi_choice)
            st.pyplot()
        else:
            st.subheader("Please select one or more charts to display.")

    elif choice in ["Reported Cases", "Mortality", "Recoveries", "Hospitalizations"]:
        st.header(chart_dict[choice][0])
        df[chart_dict[choice][1]].loc[start_date : end_date + timedelta(days=1)].plot(title = "Cumulative " + choice)
        st.pyplot()
        ax = df[chart_dict[choice][2]].loc[start_date : end_date + timedelta(days=1)].plot(title = "Daily " + choice, c='r')
        st.pyplot()

    elif choice in ["COVID ICU Patients", "COVID Ventilator Patients"]:
        st.header(chart_dict[choice][0])
        df[chart_dict[choice][1]].loc[start_date : end_date + timedelta(days=1)].plot(title = "Daily " + choice)
        st.pyplot()

    elif choice in ["Testing Information"]:
        st.header(chart_dict[choice][0])
        df[df['BCLabTests'].notnull()]['BCLabTests'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label="Total Tests", title = "Cumulative " + choice)
        df[df['BCTestNegative'].notnull()]['BCTestNegative'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label='Negative Tests')
        df[df['BCTestPositive'].notnull()]['BCTestPositive'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label='Positive Tests')
        df[df['BCTestInc'].notnull()]['BCTestInc'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label='Inconclusive Tests')
        plt.legend()
        st.pyplot()

        df[df['DBCLabTests'].notnull()]['DBCLabTests'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label="Total Tests", title = "Daily " + choice)
        df[df['DBCTestNegative'].notnull()]['DBCTestNegative'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label='Negative Tests')
        df[df['DBCTestPositive'].notnull()]['DBCTestPositive'].loc[start_date : end_date + timedelta(days=1)].abs().plot(kind='area', label='Positive Tests')
        df[df['DBCTestInc'].notnull()]['DBCTestInc'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label='Inconclusive Tests')

        plt.legend()
        st.pyplot()

    elif choice in ["Ventilator Availability", "Staffed Bed Availability"]:
        st.header(chart_dict[choice][0])
        df[chart_dict[choice][1]].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label="Total "+chart_dict[choice][3])
        df[chart_dict[choice][2]].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label='Available '+chart_dict[choice][3])
        plt.legend()
        st.pyplot()

    elif choice in ["Quarantine"]:
        st.header(chart_dict[choice][0])
        df[df[chart_dict[choice][1]].notnull()][chart_dict[choice][1]].loc[start_date : end_date + timedelta(days=1)].plot(title = "Cumulative " + choice)
        st.pyplot()
        df[df[chart_dict[choice][2]].notnull()][chart_dict[choice][2]].loc[start_date : end_date + timedelta(days=1)].plot(title = "Weekly " + choice, c='r')
        st.pyplot()

st.sidebar.markdown('&copy 2020, Lance Reinsmith')