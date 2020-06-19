cd "/Users/shahnawazakhtar/Desktop/Political Project/data/MSCI/panel"
import delimited "DID_panel.csv"


regress y intercept post treated post_treated

ologit y intercept post treated post_treated
