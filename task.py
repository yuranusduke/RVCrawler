# In this simple script, we implement a single scraper according to task:
# Collect Nationwide listings of "Motorhomes for Sale" (https://rv.campingworld.com/rvclass/motorhome-rvs) that are running on Diesel
# Capture product details (new vs old, stock #, sleeps #, length), pricing information, dealership location
# For vehicles with the sale price above $300,000 collect the horsepower

# Since we need to implement above functions flexibly that can scrape new pages according to fuel type, we use selenium

# Created by Kunhong Yu
# Date: 2023/03/14

#####################Loading packages#####################
# Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc # here we use this package to stop being blocked
# source: https://stackoverflow.com/questions/66092682/getting-blocked-by-a-website-with-selenium-and-chromedriver
#options = webdriver.ChromeOptions() 
#options.add_argument("start-maximized")
#driver = uc.Chrome(options = options)
from webdriver_manager.chrome import ChromeDriverManager
driver = webdriver.Chrome(ChromeDriverManager().install()) # use chrome as browser
from warnings import filterwarnings
filterwarnings('ignore')

# Others
import time
import sys
import pandas as pd
import argparse

#####################Main functions#####################
def waitToLoad(sleep : int, verbose = True):
	"""
	Counting down seconds to let page load
	Args : 
		--sleep: sleep seconds
		--verbose: True for showing 
	"""
	for i in range(sleep, -1, -1):
		time.sleep(1)
		if verbose:
			sys.stdout.write(f'\rWaiting for page loading {i}s.')
			sys.stdout.flush()
	if verbose:
		print()

def getHorsepower(url : str):
	"""
	Get horsepower of a vehicle
	Args : 
		--url: input url
	return : 
		--horsepower
	"""
	# note there may not exist horsepower information
	try:
		driver2 = webdriver.Chrome(ChromeDriverManager().install()) 
		driver2.get(url) # we can get this page and start to crawl
		horsepower = driver2.find_element_by_xpath('//*[@id="specs"]//child::h4[text()="HORSEPOWER"]/parent::*/h5').text.strip()

		driver2.close()
		return horsepower

	except Exception as e:
		#print(e)
		return None

def getVehiclesInfo(driver, price_limit : float):
	"""
	Since each vechile's information lies in single panel card, we here extract single page's vechiles' information
	also, for vechiles with the sale price above $300,000 collect the horsepower
	1. new or old?
	2. stock number
	3. # of sleeps
	4. length
	5. price
	6. location
	7. horsepower(optional/another page)
	Args : 
		--driver: web driver
		--price_limit
	return : 
		--a list of dictionary, containing each page's vehicles' information
	"""
	num_card = 1
	info = []
	while True:
		print(f'\tVehicle: {num_card}.', end = ' | ')
		try:
			# new or old (must have)
			newold = driver.find_element_by_xpath(f'//*[@id="pagination_container_{num_card}"]/div/div[1]/div[1]/span').get_attribute('textContent').strip()
			# stock number (must have)
			stock = driver.find_element_by_xpath(f'//*[@id="pagination_container_{num_card}"]/div/div[1]/div[2]/span[2]').get_attribute('textContent').strip()
			# number of sleeps (may not have)
			sleeps = None
			try:
				sleeps = driver.find_element_by_xpath(f'//*[@id="pagination_container_{num_card}"]//child::span[text()="Sleeps"]//parent::*').get_attribute('textContent').strip().split('\n')[-1].strip()
			except Exception as e:
				pass
			# length (must have)
			length = driver.find_element_by_xpath(f'//*[@id="pagination_container_{num_card}"]//child::span[contains(text(), "Length")]//parent::*').get_attribute('textContent').strip().split('\n')[-1].strip()
			# if price (low price) is larger than 300,000, we need to go to another page to search for horsepower
			# we must be careful with price, since some of them are in <p>, some of them are in <div>
			price = driver.find_element_by_xpath(f'//*[@id="pagination_container_{num_card}"]//child::span[@class="price-info low-price "]').get_attribute('textContent')[1:] # get rid of $ sign
			price = float(price.strip().replace(',', '')) # replace ',' with ''
			# location
			location = driver.find_element_by_xpath(f'//*[@id="pagination_container_{num_card}"]/div/div[1]/div[2]/span[1]').get_attribute('textContent').strip()
			horsepower = None
			if price > price_limit:
				# go to another page
				# get detail page's url
				detail_page_url = driver.find_element_by_xpath(f'//*[@id="pagination_container_{num_card}"]/div/div[3]/div[4]/a[2]').get_attribute("href").strip()
				horsepower = getHorsepower(detail_page_url) # get horsepower

			sinfo = {'newold' : newold, 'stock' : stock, 'sleeps' : sleeps, 'length' : length, 
					 'price' : price, 'location' : location, 'horsepower' : horsepower}
			# printing info
			print_str = ''
			for k, v in sinfo.items():
				if k == 'horsepower':
					if sinfo['horsepower'] is not None:
						print_str += str(k) + ': ' + str(v) + '; '
				else:
					print_str += str(k) + ': ' + str(v) + '; '
			print_str = print_str.rstrip('; ')
			print(print_str)

			info.append(sinfo)
			num_card += 1 # next vehicle
			waitToLoad(1, verbose = False) # to let page load
		except Exception as e:
			# print(e)
			break # break out of loop

	return info

def crawl(driver, fuel_type : str, price_limit : float):
	"""
	Crawl all items according to conditions, specfically, we can choose fuel type
	Args : 
		--driver: webdriver
		--fuel_type: string to denote fuel type
		--price_limit: we put a price limit to let it show horsepower
	"""
	print("*" * 50)
	print("Start crawling...")
	try:
		driver.get("https://rv.campingworld.com/rvclass/motorhome-rvs") # we can get this page and start to crawl
	except Exception as e:
		print(e)
		return

	# 1. find checkboxes to click them and filter
	# 1.1 choose fuel type
	check = driver.find_elements_by_css_selector('[aria-label="RV Class"]')[0]
	waitToLoad(3, verbose = True) # to let page load
	check.click() # expand
	if fuel_type == 'Diesel':
		id_ = 'classADieselFuel'
	elif fuel_type == 'Gas':
		id_ = 'classAGasFuel'
	elif fuel_type == 'Any':
		id_ = 'classAAnyFuel'
	else:
		raise ValueError('No other types of fuel!')

	print(f'Crawling for fuel_type: {fuel_type} with price_limit {price_limit} to show horsepower.')
	waitToLoad(6, verbose = True) # to let page load
	s = time.time()
	selections = driver.find_elements(By.ID, id_)
	# 1.2 filter what we need and click
	for selection in selections: selection.click()
	print(f'Updating choices...')
	waitToLoad(3, verbose = True) # to let page load # to let page load

	# 2. now, we need to get every thing we need 
	# 3. and we must can forward pages till the end, we do it by clicking next page every page
	total = 0
	sleep = 4
	all_info = []
	while True:
		total += 1
		print(f'Page: {total}')
		try:
			# here, in each page, we scrape each vehicle's information
			page_info = getVehiclesInfo(driver, price_limit)
			all_info.extend(page_info)

			page_next = driver.find_element(By.ID, 'page_next')
			# page_next.click()
			driver.execute_script('arguments[0].click()', page_next) # click here to next page, using this is to avoid page size problem
			waitToLoad(sleep, verbose = True) # to let page load
		except Exception as e:
			print('Reaching to the end')
			break

	e = time.time()
	print(f'Crawling done for {total} pages with {len(all_info)} vehicles. \nElapsed scraping time: {e - s - total * sleep: .4f}s.') # get rid of sleeping time
 	# finally, we save it to the pandas data frame
	df = pd.DataFrame(all_info, index = None)
	df.to_csv(f'scraped_data_{fuel_type}_{price_limit}.csv')


# unit test
if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument("--fuel_type", type = str, default = "Diesel", help = "Diesel/Gas/Any")
	parser.add_argument("--price_limit", type = float, default = 159000, help = "To tell if showing horsepower since we can not get vehicles more expensive than 300000")
	# we add a price limit to tell if showing horsepower since we can not get vehicles more expensive than 300000
	args = parser.parse_args()
	fuel_type = args.fuel_type
	price_limit = args.price_limit
	crawl(driver, fuel_type, price_limit)
	# usage:
	# python task.py --fuel_type 'Diesel' --price_limit 159000

