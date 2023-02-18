import pandas as pd
import yfinance as yf
from yahoofinancials import YahooFinancials
from datetime import datetime
import matplotlib.pyplot as plt
import pylab as p

# define entities to extract share price data for
tickers = ['CBA.AX','NAB.AX','VGS.AX','IVV.AX','VAS.AX','TLS.AX','BHP.AX']
entities_df = pd.DataFrame({'Entity': ['CBA','NAB','VGS','IVV','VAS','TLS','BHP']},
                           index = [0, 1, 2, 3, 4, 5, 6])

# set date range for data extract (end date is current date)
start_date = '2014-07-01'
end_date = datetime.today().strftime('%Y-%m-%d')

# get share price data from Yahoo Finance
share_data = yf.download(tickers, start=start_date, end=end_date, progress=False)

# only keep closing share price data (assume purchase price is closing price on day of purchase)
closing_price = share_data['Close']

## import share purchase information then do data type conversions:
# convert format of Trade Date, End Date and Share Split Date to mmmm-mm-dd AND format of Volume to numeric
share_purchase = pd.read_csv(r'D:\Python\Scripts\Python Shares Input.csv')
share_purchase['Trade Date'] = share_purchase['Trade Date'].astype('datetime64[ns]')
share_purchase['End Date'] = share_purchase['End Date'].astype('datetime64[ns]')
share_purchase['Share Split Date'] = share_purchase['Share Split Date'].astype('datetime64[ns]')
share_purchase["Volume"] = pd.to_numeric(share_purchase["Volume"])

# set NaN End Date entries to end date parameter of this script
cond = share_purchase['End Date'].isnull()
share_purchase.loc[cond,'End Date'] = end_date

# define final data frame for appending calculated fields onto
final_df = closing_price.reset_index()

# loop through each entity and do calculations
for i in range(len(entities_df)):
    # get daily price data and transaction data from input file
    x = entities_df.loc[i,'Entity']
    x_ax = entities_df.loc[i,'Entity']+'.AX'
    entity = closing_price.loc[:,x_ax]
    entity_share_purchase = share_purchase.loc[share_purchase['Entity'] == x]
    
    # reset index in share price data so that index is 0, 1, 2 and 3 instead of Date or whatever else (note: a new Date field will automatically get created within the entity df which we want to keep)
    entity = entity.reset_index()
    # issue with this reset index below which is not present in the single entity version of this script
    entity_share_purchase = entity_share_purchase.reset_index()

    # add purchase column for referencing later on
    entity_share_purchase['Transaction Date'] = entity_share_purchase.loc[:,'Trade Date']

    ### determine number of shares held on each date of extracted share price data
    # initialise value of shares held variable in share price data df
    entity['Number of Shares Held in '+x] = 0

    # calculate the number of shares held on any given date
    for j in range(len(entity_share_purchase)):
        for k in range(len(entity)):
            # cumulative total number of shares held 
            if entity.loc[k,'Date'] >= entity_share_purchase.loc[j,'Transaction Date'] and entity.loc[k,'Date'] <= entity_share_purchase.loc[j,'End Date']:
                # adjustments made for share splits
                if x == 'IVV' and entity.loc[k,'Date'] >= entity_share_purchase.loc[j,'Share Split Date']:
                    entity.loc[k,'Number of Shares Held in '+x] = entity.loc[k,'Number of Shares Held in '+x] + 15 * entity_share_purchase.loc[j,'Volume']
                else:
                    entity.loc[k,'Number of Shares Held in '+x] = entity.loc[k,'Number of Shares Held in '+x] + entity_share_purchase.loc[j,'Volume']

    # calculate value of holdings on any given date (note that dataframe entity gets overwritten at the start of next iteration of outer for loop)
    entity['Value of Holdings in '+x] = entity['Number of Shares Held in '+x] * entity[x_ax]

    # fill empty values with 0 (this is needed to prevent the total value of holdings being calculated as an empty value)
    entity['Value of Holdings in '+x] = entity['Value of Holdings in '+x].fillna(0)

    # merge calculated totals for each entity onto base data frame
    final_df = final_df.merge(entity, how = 'left', on = 'Date')

# calculate the total value of holdings on a given date
final_df['Total Value of Holdings'] = 0

for i in range(len(entities_df)):
    x = entities_df.loc[i,'Entity']
    final_df['Total Value of Holdings'] = final_df['Total Value of Holdings'] + final_df['Value of Holdings in '+x]

# define moving averages for share portfolio
final_df['30-Day Moving Average'] = final_df['Total Value of Holdings'].rolling(window=30).mean()
    
# output results to CSV
final_df.to_csv('Share Holdings Over Time.csv')

# output share price information for importing into MS SQL Server Management System
final_df_sql = final_df[["Date", "CBA.AX_x", "Number of Shares Held in CBA", "Value of Holdings in CBA",
                        "NAB.AX_x", "Number of Shares Held in NAB", "Value of Holdings in NAB",
                         "TLS.AX_x", "Number of Shares Held in TLS", "Value of Holdings in TLS",
                         "VGS.AX_x", "Number of Shares Held in VGS", "Value of Holdings in VGS",
                         "VAS.AX_x", "Number of Shares Held in VAS", "Value of Holdings in VAS",
                         "IVV.AX_x", "Number of Shares Held in IVV", "Value of Holdings in IVV",
                         "BHP.AX_x", "Number of Shares Held in BHP", "Value of Holdings in BHP",
                         "Total Value of Holdings"]]

final_df_sql.rename(columns = {"CBA.AX_x" : "CBA Closing Price",
                               "NAB.AX_x" : "NAB Closing Price",
                               "TLS.AX_x" : "TLS Closing Price",
                               "VGS.AX_x" : "VGS Closing Price",
                               "VAS.AX_x" : "VAS Closing Price",
                               "IVV.AX_x" : "IVV Closing Price",
                               "BHP.AX_x" : "BHP Closing Price"})

final_df_sql.to_csv('Share Holdings Time Series for SSMS.csv')


## plot times series of portfolio market value over time
# Plot everything by leveraging the very powerful matplotlib package
fig, ax = plt.subplots(figsize=(16,8))

# define x and y variables
x = final_df.loc[:,'Date']
y = final_df.loc[:,'Total Value of Holdings']

ax.plot(x, y, label='Portfolio Value ($)')

ax.set_xlabel('Date')
ax.set_ylabel('Total Portfolio Value ($)')
ax.legend(loc = 'upper left')

plt.grid(b=True)

## other plot area settings

#chart background colour
ax.set_facecolor('#ABEBC6')
# border colour
ax.figure.set_facecolor('#FDFEFE')
ax.tick_params(axis='x', colors='black')
ax.tick_params(axis='y', colors='black')

ax.set_title("PORTFOLIO VISUALIZER", color='#EF6C35', fontsize=20)

p.show()


## create pie chart of portfolio holdings
# get list of tickers and market values (these must be selected in corresponding order i.e. if select CBA ticker first then CBA market value must also be selected first)
ticker_list = []
market_values = []

for i in range(len(entities_df)):
    row_num = entities_df.index[i]

    # append entity and market values to respective vectors only if value of holdings in entity is a positive number
    if final_df.tail(1).loc[len(final_df)-1,'Value of Holdings in '+entities_df.loc[row_num,'Entity']]:
    
        ticker_list.append(entities_df.loc[row_num,'Entity'])

        entity_name = entities_df.loc[row_num,'Entity']
        entity_final_val = final_df.loc[len(final_df)-1,'Value of Holdings in ' + entity_name]

        market_values.append(entity_final_val)

# plot area settings
ax.set_facecolor('black')
ax.figure.set_facecolor('#121212')
ax.tick_params(axis='x', colors='white')
ax.tick_params(axis='y', colors='white')

ax.set_title("PORTFOLIO VISUALIZER", color='#EF6C35', fontsize=20)

# show pie chart
fig, ax = plt.subplots(figsize=(16,8))
plt.pie(market_values, labels=ticker_list, autopct = '%1.1f%%', startangle = 90)


plt.show()
    
    




