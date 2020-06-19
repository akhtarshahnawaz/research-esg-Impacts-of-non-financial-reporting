cd "/Users/shahnawazakhtar/Desktop/Political Project/data/MSCI/panel"
import delimited "RDD_panel.csv"


regress y post_cutoff running_variable

ologit y running_variable post_cutoff
