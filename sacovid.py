import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
from datetime import datetime, timedelta
import time

########################################################
############ Global constants and variables ############
########################################################

RED = "#D72827"
BLUE = "#1F77B4"
GREEN = "#2AA12B"
ORANGE = "#FF7F0F"

SA_URL = 'https://opendata.arcgis.com/datasets/48667a23f3b7468d8cd91afce7a6d047_0.geojson'

## Create dict for chart menu options
chart_dict = {
    "Reported Cases": ("Reported Cases", "total_case_cumulative", "total_case_daily_change", "total_case_7dMA"),
    "Mortality": ("Mortality Information", "deaths_cumulative", "deaths_daily_change", "deaths_7dMA"),
    # "Testing Information": ("Cumulative and Daily Testing Information", None),
    # "Recoveries": ("Cumulative and Daily Changes in Recovery / Still Ill", "Recovered", "Recovered_Daily_Change", "StillIll"),
    "ICU Information": ("COVID ICU Patients", "strac_covid_positive_in_icu"),
    "Ventilator Information": ("COVID Ventilator Patients", "strac_covid_positive_on_ventila", "strac_total_ventilators", "strac_available_ventilators"),
    "Staffed Bed Availability": ("Staffed Bed Availability Information", "strac_total_staffed_beds", "strac_available_staffed_beds"),
    "Multiview": ("Multiview Chart"),
    "Multistate Comparison": ("Comparison of Multiple States")
}

preset_dict = {
    "Daily Snapshot": ["otal_case_7dMA","deaths_7dMA","strac_covid_positive_in_icu","strac_covid_positive_on_ventila"],
}

## Multiview chart options
multiview_options = {
    "Cumulative Reported Cases": "total_case_cumulative",
    "Daily Reported Cases": "total_case_daily_change",
    "Reported Cases 7dMA": "total_case_7dMA",
    "Cumulative Mortality": "deaths_cumulative",
    "Daily Mortality": "deaths_daily_change",
    "Daily Mortality 7dMA": "deaths_7dMA",
    # "Cumulative Recoveries": "Recovered",
    # "Daily Change in Recoveries": "Recovered_Daily_Change",
    # "Still Ill Patients": "StillIll",
    "Daily COVID ICU Census": "strac_covid_positive_in_icu",
    "Daily COVID Ventilator Census":"strac_covid_positive_on_ventila",
    # "Daily Positive Tests": "DBCTestPositive",
    # "Daily Positive Tests 7dMA": "DBCTestPositive7dMA",
    # "Test Positivity Rate 7dMA (%)": "TestPositivityRate"
}

state_graph_types = {
    "Total Confirmed Cases": 'positive', 
    "Confirmed Cases per 100K Population": 'positive_per100k',
    "Daily New Cases 7d Moving Average": 'positiveIncrease_7dMA',
    "Daily New Cases per 100K Pop, 7dMA": 'positiveIncrease_7dMA_per100k',
    "Total Confirmed Deaths": 'death', 
    "Confirmed Deaths per 100K Population": 'death_per100k',
    "Daily New Deaths 7d Moving Average": 'deathIncrease_7dMA',
    "Daily New Deaths per 100K Pop, 7dMA": 'deathIncrease_7dMA_per100k',
    "Test Positivity Rate 7d Moving Average(%)": 'testPositivity_7dMA'
}


########################################################
############## Helper Functions ########################
########################################################

def format_func(value, tick=None):
    num_thousands = 0 if abs(value) < 1000 else 1
    value = round(value / 1000**num_thousands, 2)
    return f'{value:g}'+' K'[num_thousands]

def callAPI():
    r = requests.get(SA_URL)
    jsonobj = r.json()
    dictlist = [i['properties'] for i in jsonobj['features']]    
    return pd.DataFrame(dictlist)

########################################################
############## Data Fetch Functions ####################
########################################################

@st.cache(ttl=60*6)
def fetch_san_antonio():
    df = callAPI()
    # Set Date to index as datetime
    df['reporting_date'] = pd.to_datetime(df['reporting_date'])
    df.set_index('reporting_date', inplace=True, drop=True)
    # Get rid of dates without data
    df = df[df.index.notnull()]
    ## Create additional columns
    # Daily change in recovered cases
    df["Recovered_Daily_Change"] = (df['Recovered'] - df['Recovered'].shift(1)).dropna()
    # Reported cases 7 day moving average
    df["total_case_7dMA"] = df["total_case_daily_change"].rolling(7).mean()
    # Daily Mortality 7 day moving average
    df["deaths_7dMA"] = df["deaths_daily_change"].rolling(7).mean()
    # Daily Positive Cases 7 day moving average
    df["DBCTestPositive7dMA"] = df["DBCTestPositive"].rolling(7).mean()
    # Test positivity rate
    df["TestPositivityRate"] = (df["DBCTestPositive"] / df["DBCLabTests"]).rolling(7).mean()*100
    return df

@st.cache
def fetch_state_pops():
    return pd.read_csv('states.csv', index_col=0)

@st.cache
def fetch_state(state_abbrev):
    population =state_pops.loc[state_abbrev]['2018 Population']
    df = pd.read_json(f'https://covidtracking.com/api/v1/states/{state_abbrev.lower()}/daily.json')
    df['date'] = pd.to_datetime(df['date'], format="%Y%m%d")
    df.set_index('date', inplace=True)
    df.sort_index(ascending=True, inplace=True)
    for field in ['positiveIncrease', 'deathIncrease']:
        df[field+'_7dMA'] = df[field].rolling(7).mean()
        df[field + '_7dMA_per100k'] = df[field+'_7dMA']/population*100000
    for field in ['positive', 'death']:
        df[field + '_per100k'] = df[field]/population*100000
    df['testPositivity_7dMA'] = (df['positiveIncrease'] / df['totalTestResultsIncrease']).rolling(7).mean() * 100
    return df

sa_df = fetch_san_antonio()
state_pops = fetch_state_pops()

########################################################
############## Graph Drawing Functions #################
########################################################

def make_state_graphs(state_dict, state_graph_types, start_date, end_date):
    graph_descs = st.multiselect("Select graphs to display:", 
                    options=list(state_graph_types.keys()),
                    default=[list(state_graph_types.keys())[i] for i in [3,1,7,5,8]])
    for graph_desc in graph_descs:
        for state, df in state_dict.items():
            df[state_graph_types[graph_desc]].loc[start_date : end_date + timedelta(days=1)].plot(label=state.upper(), title=graph_desc, figsize=(8,6))
        if graph_desc == "Test Positivity Rate 7d Moving Average(%)":
            plt.ylim(0,100)
            plt.xlabel("Data are not likely reliable on earlier dates when testing was less available.")
        else:
            plt.xlabel("Date")
        plt.legend([key.upper() for key in state_dict.keys()], loc='upper left')
        st.pyplot()
    

def make_sa_chart(df, choice, start_date, end_date):
    if choice in ["Multiview"]:
        st.header(chart_dict[choice])
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

    elif choice in preset_dict.keys():
        st.header("Preset: " + choice)
        multi_choice = preset_dict[choice]
        if len(multi_choice) > 0:
            ax = df[[multiview_options[x] for x in multi_choice] ].loc[start_date : end_date + timedelta(days=1)].plot(title="Multiview Chart")
            ax.legend(multi_choice)
            st.pyplot()

    elif choice in ["Multistate Comparison"]:
        st.header(chart_dict[choice])
        st.subheader("These charts allow comparison between different states using raw and population-adjusted data.")
        state_names = st.multiselect("Select states to display:",
                        options=state_pops['State'].tolist(),
                        default=state_pops['State'].tolist()[:4])
        if len(state_names) > 0:
            state_abbrevs = state_pops.index[state_pops['State'].isin(state_names)].tolist()   
            state_dict = {}
            for state_abbrev in state_abbrevs:
                state_df = fetch_state(state_abbrev)
                state_dict[state_abbrev] = state_df
            make_state_graphs(state_dict, state_graph_types, start_date, end_date)
        else:
            st.subheader("Please select one or more states to display.")

    elif choice in ["Testing Information"]:
        st.header(chart_dict[choice][0])

        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        ax1.set_ylabel("")
        ax2.set_ylabel("Test Positivity Rate 7dMA (%)", rotation=270, labelpad=10, c='gray')
        ax2.tick_params(axis='y', colors='gray')
        ax2.set_ylim(0,100)
        df[df['BCLabTests'].notnull()]['BCLabTests'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label="Total Tests", title="Cumulative " + choice, ax=ax1)
        df[df['BCTestNegative'].notnull()]['BCTestNegative'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label='Negative Tests', ax=ax1)
        df[df['BCTestPositive'].notnull()]['BCTestPositive'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label='Positive Tests', ax=ax1)
        df['TestPositivityRate'].loc[start_date : end_date + timedelta(days=1)].abs().plot(label='Test Positivity Rate', c='white', ax=ax2)
        ax1.legend()
        st.pyplot()

        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        ax1.set_ylabel("")
        ax2.set_ylabel("Test Positivity Rate 7dMA (%)", rotation=270, labelpad=10, c='gray')
        ax2.tick_params(axis='y', colors='gray')
        ax2.set_ylim(0,100)
        df[df['DBCLabTests'].notnull()]['DBCLabTests'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label="Total Tests", title="Daily " + choice, ax=ax1)
        df[df['DBCTestNegative'].notnull()]['DBCTestNegative'].loc[start_date : end_date + timedelta(days=1)].plot(kind='area', label='Negative Tests', ax=ax1)
        df[df['DBCTestPositive'].notnull()]['DBCTestPositive'].loc[start_date : end_date + timedelta(days=1)].abs().plot(kind='area', label='Positive Tests', ax=ax1)
        df['TestPositivityRate'].loc[start_date : end_date + timedelta(days=1)].abs().plot(label='Test Positivity Rate', c='white', ax=ax2)
        ax1.legend()
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

########################################################
############## Site Construction Function ##############
########################################################

def build_site():
    start_time = time.time()
    start_date = st.sidebar.date_input("Start Date", value=datetime(2020, 3, 19))
    end_date = st.sidebar.date_input("End Date", value=sa_df.index.max())

    presets = st.sidebar.multiselect("Select preset charts to display:",
                            options=list(preset_dict.keys()))

    choices = st.sidebar.multiselect("Select individual charts to display:",
                            options=list(chart_dict.keys()),
                            default=list(chart_dict.keys())[:3])

    choices = presets + choices

    st.sidebar.markdown('### HELP:\n* Enter your start and stop dates.\n* Click in the box below the dates to select individual charts to display.\n'
                        '* __Multiview__ allows for viewing multiple graphs in one chart.\n'
                        '* __Multistate Comparison__ allows comparison between different states using raw and population-adjusted data.\n'
                        '* Charts display in the order they are selected.  __Remember to scroll down to see all of the charts.__')


    ## Render the main screen
    st.title("San Antonio COVID-19 Charts")
    st.markdown(f'The data for these charts were last updated on {str(sa_df.index.max()).split()[0]}. '
                'See HELP in sidebar to the left.')
    st.markdown('')

    if len(choices) == 0:
        st.header('Select at least one chart in the sidebar to show below.')
    else:    
        for choice in choices:
            make_sa_chart(sa_df, choice, start_date, end_date)

    st.subheader('Sources:')
    st.markdown(SA_URL)
    st.markdown('https://covidtracking.com/')

    st.sidebar.markdown('&copy 2020, Lance Reinsmith')
    st.write(f"Page render time: {round(time.time()-start_time, 4)} sec")

if __name__ == "__main__":
    build_site()