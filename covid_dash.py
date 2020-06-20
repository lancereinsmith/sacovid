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

for col in ['COVIDnICU', 'COVIDonVent']:
    df[col + "_Cum"] = df[col].cumsum()

## Create dict for chart options
chart_dict = {
    "Reported Cases": ("Cumulative and Daily Reported Cases", "ReportedCum", "ReportedOn"),
    "Testing Information": ("Cumulative and Daily Testing Information", None, None),
    "Mortality": ("Cumulative and Daily Mortality Information", "DeathsCum", "Deceased"),
    "Recoveries": ("Cumulative and Daily Recovery Information", "Recovered", "Recovered_Daily"),
    "Hospitalizations": ("Cumulative and Daily Hospitalization Information", "Hospitalized", "Hospitalized_Daily"),
    "COVID ICU Patients": ("Cumulative and Daily COVID ICU Patients", "COVIDnICU_Cum", "COVIDnICU"),
    "COVID Ventilator Patients": ("Cumulative and Daily COVID Ventilator Patients", "COVIDonVent_Cum", "COVIDonVent"),
    "Quarantine": ("Cumulative and Weekly Quarantine Information", "EverQuar", "WeekQuar"),
    "Ventilator Availability": ("Ventilator Availability Information", "TotalVents", "AvailVent", "Ventilators"),
    "Staffed Bed Availability": ("Staffed Bed Availability Information", "TotalStaffedBeds", "AvailStaffedBeds", "Staffed Beds")
}

## Sidebar
if st.sidebar.checkbox("See source data"):
    st.write("Source data:")
    st.write(URL)
    st.dataframe(df)

start_date = st.sidebar.date_input("Start Date", value=datetime(2020, 3, 19))
end_date = st.sidebar.date_input("End Date", value=df.index.max())

options_list = ["Reported Cases",
                "Testing Information",
                "Mortality",
                "Recoveries",
                "Hospitalizations",
                "COVID ICU Patients",
                "COVID Ventilator Patients",
                "Quarantine",
                "Ventilator Availability",
                "Staffed Bed Availability"
                ]

choices = st.sidebar.multiselect("Select individual charts to display:",
                        options=options_list,
                        default=options_list[:2])

st.sidebar.markdown('### HELP:\n* Enter your start and stop dates.\n* Click the magnifying glass to select charts to display.  Or, type a keyword in the search bar.')

## Render the main screen
st.markdown("# San Antonio COVID-19 Charts")
st.markdown(f'#### The data for these charts were last updated at {df.index.max()}. Source:')
st.code(URL)

for choice in choices:
    if choice in ["Reported Cases", "Mortality", "Recoveries", "Hospitalizations", "COVID ICU Patients", "COVID Ventilator Patients"]:
        st.markdown("## "+chart_dict[choice][0])
        df[chart_dict[choice][1]].loc[start_date : end_date + timedelta(days=1)].plot(title = "Cumulative " + choice)
        st.pyplot()
        ax = df[chart_dict[choice][2]].loc[start_date : end_date + timedelta(days=1)].plot(title = "Daily " + choice, c='r')
        st.pyplot()

    elif choice in ["Testing Information"]:
        st.markdown("## "+chart_dict[choice][0])
        df[df['BCLabTests'].notnull()]['BCLabTests'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label="Total Tests", title = "Cumulative " + choice)
        df[df['BCTestNegative'].notnull()]['BCTestNegative'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label='Negative Tests')
        df[df['BCTestPositive'].notnull()]['BCTestPositive'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label='Positive Tests')
        df[df['BCTestInc'].notnull()]['BCTestInc'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label='Inconclusive Tests')
        plt.legend();
        st.pyplot()

        df[df['DBCLabTests'].notnull()]['DBCLabTests'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label="Total Tests", title = "Daily " + choice)
        df[df['DBCTestNegative'].notnull()]['DBCTestNegative'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label='Negative Tests')
        df[df['DBCTestPositive'].notnull()]['DBCTestPositive'].loc[start_date : end_date + timedelta(days=1)].abs().plot(kind='area', label='Positive Tests')
        df[df['DBCTestInc'].notnull()]['DBCTestInc'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label='Inconclusive Tests')

        plt.legend();
        st.pyplot()

    elif choice in ["Ventilator Availability", "Staffed Bed Availability"]:
        st.markdown("## "+chart_dict[choice][0])
        df[chart_dict[choice][1]].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label="Total "+chart_dict[choice][3])
        df[chart_dict[choice][2]].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label='Available '+chart_dict[choice][3])
        plt.legend()
        st.pyplot()

    elif choice in ["Quarantine"]:
        st.markdown("## "+chart_dict[choice][0])
        df[df[chart_dict[choice][1]].notnull()][chart_dict[choice][1]].loc[start_date : end_date + timedelta(days=1)].plot(title = "Cumulative " + choice)
        st.pyplot()
        df[df[chart_dict[choice][2]].notnull()][chart_dict[choice][2]].loc[start_date : end_date + timedelta(days=1)].plot(title = "Weekly " + choice, c='r')
        st.pyplot()

st.sidebar.markdown('&copy 2020, Lance Reinsmith')