import pandas as pd
import numpy as np
import requests 
import pickle
from unidecode import unidecode
import requests, urllib
from bs4 import BeautifulSoup
from selenium import webdriver
import os

#####################################################################################
# This Function finds identification id and encoded title for each company on MSCI
#####################################################################################
def get_identifiers(company_df, start_from_company=False):
    # Request Parameters
    URL = "https://www.msci.com/esg-ratings"
    PARAMS = {
        "p_p_id" : "esgratingsprofile",
        "p_p_lifecycle" : 2,
        "p_p_resource_id" : "searchEsgRatingsProfiles",
        "_esgratingsprofile_keywords" : "msft"
    }

    # Setup Variables
    total_found = 0
    
    start_from = 0
    if start_from_company:
        start_from = company_df["Company name"].values.tolist().index(start_from_company)
    
    output = []
    if os.path.exists("tmp/company_identifier.lst"):
        output = pickle.load(open( "tmp/company_identifier.lst", "rb" ) )
        

    # Scrapping Loop
    for i,company in enumerate(company_df["Company name"].values.tolist()[start_from:]):
        if type(company) != unicode:
            company = unicode(company, "utf-8")
            
        PARAMS["_esgratingsprofile_keywords"] = company.split(" ")[0]
        r = requests.get(url = URL, params = PARAMS)
        result = r.json()
        
        if len(result) > 0:
            total_found += 1
            output += result

        if i%100 == 0:
            pickle.dump(output, open("tmp/company_identifier.lst", "wb"))
            print company, "{} of {} found".format(total_found, i)
    return output


#####################################################################################
# This Function Standardizes strings so that they can be compared across tables
#####################################################################################
def standardize_string(string):
    alpha_numeric = lambda x: "".join(e for e in x if e.isalpha() or e == " ").strip().upper()
    if type(string) == int or type(string) == float:
        string = str(string)
        
    if type(string) != unicode:
        string = unicode(string, "utf-8")
    string = unidecode(string)
    string = alpha_numeric(string)
    return string
        
#####################################################################################
# This Function Parses Page using BeautifulSoup to get Actual data
#####################################################################################
def extract_soup(soup, company_id, company_title):
    print company_id, company_title
    
    this_soup = {
        "date":[],
        "rating_history":[],
        "rating":[],
        "percent_rating":[],
    }
    
    # Getting Rating History at various dates
    for item in soup.find_all("g", { "class" : "highcharts-axis-labels" })[0]:
        this_soup["date"].append(item.find(text = True))

    for item in soup.find_all("g", { "class" : "highcharts-data-labels" })[0]:
        this_soup["rating_history"].append(item.find(text = True))

    # Getting Distribution of Ratings
    for item in soup.find_all("g", { "class" : "highcharts-axis-labels" })[1]:
        this_soup["rating"].append(item.find(text = True))

    for item in soup.find_all("g", { "class" : "highcharts-data-labels" })[1]:
        this_soup["percent_rating"].append(item.find(text = True))

    # Category-wise situation
    for item in soup.find("div", { "class" : "comparison-table" }).find_all("div", { "class" : "comparison-column" }):
        for v in item.find_all("div", { "class" : "comparison-body" }):
            categories = [i.find(text=True) for i in v.find_all("span")]

        this_soup[item.find("div", { "class" : "comparison-header" }).find(text=True)] = categories

    # Scrap Country and Industry
    this_soup["industry"] = soup.find("div", { "class" : "header-esg-industry" }).find("b").next_sibling.strip()
    this_soup["country"] = soup.find("div", { "class" : "header-country" }).find("b").next_sibling.strip()

    return this_soup

#####################################################################################
# This Function returns actual data once we pass it amadeus and msci merged table
#####################################################################################
def extract_data(merged_dataframe):
    msci_extracted = {}
    for etitle, url in zip(merged_dataframe["encodedTitle"], merged_dataframe["url"]):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        browser = webdriver.Chrome("./chromedriver",options=chrome_options)
        browser.get("https://www.msci.com/esg-ratings/issuer/{}/{}".format(etitle, url))
        soup = BeautifulSoup(browser.page_source, "html.parser")
        msci_extracted[url] = extract_soup(soup, url, etitle)
        browser.quit()
    return msci_extracted

#####################################################################################
# This Function cleans our extracted data
#####################################################################################
def clean_df(data_extract_df):
    data_extract_df["AVERAGE"] = data_extract_df["AVERAGE"].apply(lambda x: ",".join([i.strip() for i in x]))
    data_extract_df["ESG LAGGARD"] = data_extract_df["ESG LAGGARD"].apply(lambda x: ",".join([i.strip() for i in x]))
    data_extract_df["ESG LEADER"] = data_extract_df["ESG LEADER"].apply(lambda x: ",".join([i.strip() for i in x]))

    data_extract_df["AVERAGE"] = data_extract_df["AVERAGE"].apply(lambda x: np.nan if "does not" in x else x)
    data_extract_df["ESG LAGGARD"] = data_extract_df["ESG LAGGARD"].apply(lambda x: np.nan if "not a" in x else x)
    data_extract_df["ESG LEADER"] = data_extract_df["ESG LEADER"].apply(lambda x: np.nan if "not a" in x else x)

    data_extract_df["rating"] = data_extract_df["rating"].apply(lambda x: x[1:])
    data_extract_df["date"] = data_extract_df["date"].apply(lambda x: ",".join([i.strip() for i in x]))
    data_extract_df["percent_rating"] = data_extract_df["percent_rating"].apply(lambda x: ",".join([i.strip() for i in x]))
    data_extract_df["rating"] = data_extract_df["rating"].apply(lambda x: ",".join([i.strip() for i in x]))
    data_extract_df["rating_history"] = data_extract_df["rating_history"].apply(lambda x: ",".join([i.strip() for i in x]))
    
    return data_extract_df