# use selenium to get latest price data from live games on betfair, smarkets, matchbook and others
# every 5 seconds, get the new odds data and liquidity
# arbs are when lay prices are lower than back prices

import requests, bs4, time, os, threading
from selenium import webdriver

import cv2, pytesseract, PIL
pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
    
chrome_options = webdriver.ChromeOptions()

chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--ignore-certificate-errors-spki-list')
chrome_options.add_argument('--ignore-ssl-errors')

chrome_options.binary_location = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

########################################################################
# at the start of the program, get all games for betfair that day and using the list of today's games from smarkets, discard those not in betfair
# create a thread to check all betfair live game odds every second 
# create a separate thread for each live smarkets games using selenium and check each every second
# with each check of the odds for a game, record the results to a function that can be accessed by both the smarkets and betfair threads
# when an arb is found by comparing the odds recorded in the above function, notify
# stop getting data for relevant game when betfair market for the match odds returns an error, as game has ended
# don't forget 5% and 2% comission

# set up betfair 
import betfairlightweight 
from betfairlightweight import filters

print('setting up betfair api')

trading = betfairlightweight.APIClient(username='bill.bernardot@gmail.com',
                                      password='Betting@Pass2>',
                                      app_key='2ylsB5KQOdsPpE04',
                                      certs=r'C:\Program Files\OpenSSL-Win64\bin\cnf')
trading.login()

event_types = trading.betting.list_event_types()
football_event_filter = betfairlightweight.filters.market_filter(event_type_ids=[1],
                                                                 in_play_only=True,
                                                                  market_start_time={'from':'2020-07-30T00:00:00Z',
                                                                                    'to':'2020-07-31T00:00:00Z'})
football_events_raw = trading.betting.list_events(filter=football_event_filter)
football_events = [(event_object.event.name, event_object.event.id) for event_object in football_events_raw]
print(len(football_events))

# get smarkets games, discard games not shared with betfair
print('getting smarkets games')
res = requests.get('https://smarkets.com/listing/sport/football?period=today')
res.raise_for_status()
soup = bs4.BeautifulSoup(res.text, "html.parser")

games = soup.select('.event-list .overlay')
urls = ['https://smarkets.com'+game.get('href') for game in games]
print(f'no. of games: {len(urls)}')

smarkets_data = []
for url in urls:
    # get event page
    res = requests.get(url)
    try:
        res.raise_for_status()
    except Exception as e:
        print(e)
        
    soup = bs4.BeautifulSoup(res.text, "html.parser")
    competitors = ' v '.join([team.getText() for team in soup.select('h1')])
    # get rid of accents to make comparison with betfair games
    import unidecode 
    competitors = unidecode.unidecode(competitors)
    print(f'{competitors}')
    smarkets_data.append([competitors, url])
    

    
# get longest word in betfair str(game) from both before & after ' v '
# if either or both words are found in the relevant home/away position, game has been found
matching_games = []
for game,id in football_events:
    words,whitespace = [],[]
    for c,char in enumerate(game):
        if char == ' ' or c == len(game)-1:
            if len(words) == 0:
                words.append(game[:c])
            elif c == len(game)-1:
                words.append(game[whitespace[-1]+1:])
            else:
                words.append(game[whitespace[-1]+1:c])
            whitespace.append(c)
    
    v = words.index('v')
    test = [len(words[0]),words[0]]
    for c,word in enumerate(words):
        if c == v:
            home_longest_word = test[1]
            test = [len(word),word] # set to 'v' to ensure longest word from EACH team
        if len(word) > test[0]:
            test = [len(word),word] # update to the longest word yet
        if c == len(words)-1:
            away_longest_word = test[1]
    
    print(home_longest_word, away_longest_word)
    
    for match,url in smarkets_data:
        v = match.index('v')
        if home_longest_word in match[:v] or away_longest_word in match[v:]:
            matching_games.append([game,id,match,url])
            
print('\n',matching_games, len(matching_games))



# upon instantiating class, create dictionary of games to be scanned where key=name of game, value=odds of game
# betfair thread updates the value for the relevant game with each scan, and smarkets thread compares to the odds it has just found to identify arbs
# smarkets does not update the dictionary, ONLY betfair does

# create one thread for getting betfair data
# create as many threads for smarkets as no. of games to scan
class ArbCatcher:
    def __init__(self):
        self.betfair_odds = {}
        self.lock = threading.Lock()
        
    def smarkets_worker(self, game_name,game,url):
        game_name = game_name.replace(' ','_')
        # get full time result
        driver = webdriver.Chrome('chromedriver.exe',options = chrome_options)
        driver.set_window_size(1920, 1080)
        driver.get(url)
        time.sleep(10)
        while True: # should stop when game has ended, not forever
            
            
            # need to halt all other smarkets threads whilst only one thread at a time goes through each iteration of this loop
            # otherwise different threads start accessing values from other threads and its very chaotic and buggy
            # get hold of the threading lock to block threads from modifying smarkets_match_odds
            self.lock.acquire()
            time.sleep(2)
            try:
                smarkets_match_odds = []
                for i in range(1,4):
                    team = driver.find_element_by_xpath(f"//ul[@class='contract-groups']/li[1]/div/div[2]/div/ul/li[{i}]/div/div/div/span").text # team
                    # back
                    back_odds = driver.find_element_by_xpath(f"//ul[@class='contract-groups']/li[1]/div/div[2]/div/ul/li[{i}]/div/span[2]/span/span[1]").text # odds
                    back_volume = driver.find_element_by_xpath(f"//ul[@class='contract-groups']/li[1]/div/div[2]/div/ul/li[{i}]/div/span[2]/span/span[2]").text # volume
                    # lay 
                    lay_odds = driver.find_element_by_xpath(f"//ul[@class='contract-groups']/li[1]/div/div[2]/div/ul/li[{i}]/div/span[3]/span/span[1]").text # odds
                    lay_volume = driver.find_element_by_xpath(f"//ul[@class='contract-groups']/li[1]/div/div[2]/div/ul/li[{i}]/div/span[3]/span/span[2]").text # volume
                    smarkets_match_odds.append([team, back_odds, back_volume[1:], lay_odds, lay_volume[1:]]) # get rid of '£' sign
                    
                    for key in self.betfair_odds:
                        if key == game_name: # game_name will always be the relevant smarkets game to betfair
                            # calculate p/l for back/lay
                            # presuming £10 back stake
                            betfair_home_odds = [str(self.betfair_odds[key][0][1]), str(self.betfair_odds[key][0][3]), 
                                                 str(self.betfair_odds[key][0][2]), str(self.betfair_odds[key][0][4])] # back,lay,back volume, lay volume
                            betfair_away_odds = [str(self.betfair_odds[key][1][1]), str(self.betfair_odds[key][1][3]), 
                                                 str(self.betfair_odds[key][1][2]), str(self.betfair_odds[key][1][4])] # back,lay,back volume, lay volume
                            betfair_draw_odds = [str(self.betfair_odds[key][2][1]), str(self.betfair_odds[key][2][3]), 
                                                 str(self.betfair_odds[key][2][2]), str(self.betfair_odds[key][2][4])] # back,lay,back volume, lay volume
                            
                            # home match odds
                            if len(smarkets_match_odds) == 1:
                                # betfair lay < smarkets back
                                if float(betfair_home_odds[1]) < float(smarkets_match_odds[0][1]):
                                    print(f'\n\n\n\n{game_name} HOME betfair lay {betfair_home_odds[1],betfair_away_odds[3]} < smarkets back {smarkets_match_odds[0][1],smarkets_match_odds[0][2]}')
                                    # backing smarkets, laying betfair
                                    lay_stake = ((float(smarkets_match_odds[0][1])*10) - (((float(smarkets_match_odds[0][1])-1)*10)*0.05)) / float(betfair_home_odds[1])
                                    lay_liability = lay_stake * (float(betfair_home_odds[1])-1)
                                    back_profit = (((float(smarkets_match_odds[0][1])-1)*10) - (((float(smarkets_match_odds[0][1])-1)*10)*0.02)) - lay_liability
                                    lay_profit = (lay_stake - 10)
                                    print(back_profit,lay_profit, lay_stake, lay_liability)
                                # smarkets lay < betfair back    
                                if float(betfair_home_odds[0]) > float(smarkets_match_odds[0][3]):
                                    print(f'\n\n\n\n{game_name} HOME betfair back {betfair_home_odds[0],betfair_away_odds[2]} > smarkets lay {smarkets_match_odds[0][3],smarkets_match_odds[0][4]}')
                                    # backing betfair, laying smarkets
                                #print(smarkets_match_odds[0])
                                    
                            # draw match odds
                            elif len(smarkets_match_odds) == 2:
                                # betfair lay < smarkets back
                                if float(betfair_draw_odds[1]) < float(smarkets_match_odds[1][1]):
                                    print(f'\n\n\n\n{game_name} DRAW betfair lay {betfair_draw_odds[1],betfair_away_odds[3]} < smarkets back {smarkets_match_odds[1][1], smarkets_match_odds[1][2]}')
                                    # backing smarkets, laying betfair
                                    lay_stake = ((float(smarkets_match_odds[1][1])*10) - (((float(smarkets_match_odds[1][1])-1)*10)*0.05)) / float(betfair_draw_odds[1])
                                    lay_liability = lay_stake * (float(betfair_draw_odds[1])-1)
                                    back_profit = (((float(smarkets_match_odds[1][1])-1)*10) - (((float(smarkets_match_odds[1][1])-1)*10)*0.02)) - lay_liability
                                    lay_profit = (lay_stake - 10)
                                    print(back_profit,lay_profit, lay_stake, lay_liability)
                                # smarkets lay < betfair back    
                                if float(betfair_draw_odds[0]) > float(smarkets_match_odds[1][3]):
                                    print(f'\n\n\n\n{game_name} DRAW betfair back {betfair_draw_odds[0],betfair_away_odds[2]} > smarkets lay {smarkets_match_odds[1][3], smarkets_match_odds[1][4]}')
                                    # backing betfair, laying smarkets
                                #print(smarkets_match_odds[1])
                                    
                            # away match odds
                            elif len(smarkets_match_odds) == 3:
                                # betfair lay < smarkets back
                                if float(betfair_away_odds[1]) < float(smarkets_match_odds[2][1]):
                                    print(f'\n\n\n\n{game_name} AWAY betfair lay {betfair_away_odds[1],betfair_away_odds[3]} < smarkets back {smarkets_match_odds[2][1],smarkets_match_odds[2][2]}')
                                    # backing smarkets, laying betfair
                                    lay_stake = ((float(smarkets_match_odds[2][1])*10) - (((float(smarkets_match_odds[2][1])-1)*10)*0.05)) / float(betfair_away_odds[1])
                                    lay_liability = lay_stake * (float(betfair_away_odds[1])-1)
                                    back_profit = (((float(smarkets_match_odds[2][1])-1)*10) - (((float(smarkets_match_odds[2][1])-1)*10)*0.02)) - lay_liability
                                    lay_profit = (lay_stake - 10)
                                    print(back_profit,lay_profit, lay_stake, lay_liability)
                                # smarkets lay < betfair back    
                                if float(betfair_away_odds[0]) > float(smarkets_match_odds[2][3]):
                                    print(f'\n\n\n\n{game_name} AWAY betfair back {betfair_away_odds[0],betfair_away_odds[2]} > smarkets lay {smarkets_match_odds[2][3],smarkets_match_odds[2][4]}')
                                    # backing betfair, laying smarkets
                                #print(smarkets_match_odds[2])
                            
                    
            except Exception as e:
                print(f'smarkets match odds: {e}')
                
            try:
                #
                #
                # if page is reloaded and market had ended eg 0.5 goals because goal has been scored, 
                # the tab will dissapear and other markets won't be found as xml would have changed
                #
                driver.execute_script("window.scrollTo(0, 800)")
                zero_five_btn = driver.find_element_by_xpath('/html/body/div[2]/div[2]/div[2]/div/div/div[3]/main/ul/li[6]/div/div/div[1]/div[2]/div/button[1]')
                zero_five_btn.click()
                
                smarkets_zero_five_odds = []
                for i in range(1,3):
                    market_name = driver.find_element_by_xpath(
                        f'/html/body/div[2]/div[2]/div[2]/div/div/div[3]/main/ul/li[6]/div/div[2]/div/ul/li[{i}]/div[1]/div/div[1]/span/span').text # team
                    # back
                    back_odds = driver.find_element_by_xpath(
                        f'/html/body/div[2]/div[2]/div[2]/div/div/div[3]/main/ul/li[6]/div/div[2]/div/ul/li[{i}]/div[1]/span[2]/span[1]/span[1]').text # odds
                    back_volume = driver.find_element_by_xpath(
                        f'/html/body/div[2]/div[2]/div[2]/div/div/div[3]/main/ul/li[6]/div/div[2]/div/ul/li[{i}]/div[1]/span[2]/span[1]/span[2]').text # volume
                    # lay 
                    lay_odds = driver.find_element_by_xpath(
                        f'/html/body/div[2]/div[2]/div[2]/div/div/div[3]/main/ul/li[6]/div/div[2]/div/ul/li[{i}]/div[1]/span[3]/span[1]/span[1]').text # odds
                    lay_volume = driver.find_element_by_xpath(
                        f'/html/body/div[2]/div[2]/div[2]/div/div/div[3]/main/ul/li[6]/div/div[2]/div/ul/li[{i}]/div[1]/span[3]/span[1]/span[2]').text # volume
                    smarkets_zero_five_odds.append([market_name, back_odds, back_volume[1:], lay_odds, lay_volume[1:]]) # get rid of '£' sign   
                    
                
                print(smarkets_zero_five_odds)
                
            except Exception as e:
                print(f'smarkets: {e}')
                
                
            self.lock.release()
            #print(smarkets_match_odds)
            #print(self.betfair_odds)

    def betfair_worker(self, matching_games):
        while True:
            time.sleep(2)
            for game in matching_games:
                game_name = game[0].replace(' ','_')

                market_catalogue_filter = betfairlightweight.filters.market_filter(event_ids=[game[1]])
                market_catalogues = trading.betting.list_market_catalogue(filter=market_catalogue_filter, max_results=500)
                markets = [(market_cat_object.market_id, market_cat_object.market_name, market_cat_object.total_matched) for market_cat_object in market_catalogues]
                match_odds_id = [item[0] if item[1] == 'Match Odds' else '' for item in markets]

                price_filter = betfairlightweight.filters.price_projection(price_data=['EX_BEST_OFFERS'])
                market_books = trading.betting.list_market_book(market_ids=[match_odds_id], price_projection=price_filter)
                runners = market_books[0].runners
                #print(game[0])
                try:
                    match_odds = [(runner.selection_id, 
                            runner.ex.available_to_back[0].price, 
                            runner.ex.available_to_back[0].size, 
                            runner.ex.available_to_lay[0].price,
                            runner.ex.available_to_lay[0].size) for runner in runners]
                    self.betfair_odds[game_name] = match_odds
                except Exception as e:
                    print(f'betfair: {e}')


ArbCatcher = ArbCatcher()
smarkets_threads = []
betfair_threads = []
betfair_thread = threading.Thread(target=ArbCatcher.betfair_worker, args=(matching_games,))
betfair_thread.start()
betfair_threads.append(betfair_thread)
for game in matching_games:
    smarkets_thread = threading.Thread(target=ArbCatcher.smarkets_worker, args=(game[0],game[2],game[3]))
    smarkets_thread.start()
    smarkets_threads.append(smarkets_thread)
    time.sleep(3) # because each thread starts by requesting access to smarkets, results in many requests all at once which smarkets ends up blocking
    
    
'''s = [thread.join() for thread in threads] # wait for all threads to end before continuing main thread
print('all threads completed')'''




        
'''
##### try using beautiful soup for betfair/betdaq?

def betdaq_worker(game):     
    res = requests.get('https://www.betdaq.com/exchange/soccer/english-soccer/premier-league/premier-league-matches/18-00-sheff-utd-v-everton-(live)/7391365')
    try:
        res.raise_for_status()
    except Exception as e:
        print(e)
        time.sleep(2)
    finally: # could cause error as raise_for_status() called no matter what
        res.raise_for_status()
    print(bs4.BeautifulSoup(res.text, "html.parser"))
    driver = webdriver.Chrome('chromedriver.exe',options=chrome_options)
    driver.set_window_size(1920, 1080)
    driver.implicitly_wait(10)
    failed = True
    while failed:
        try:
            driver.get('https://www.betdaq.com/exchange/soccer/english-soccer/premier-league/premier-league-matches/18-00-sheff-utd-v-everton-(live)/7391365')
            failed = False
        except Exception as e:
            print('error'+e)
            time.sleep(2)
    time.sleep(5)
    search_input = driver.find_element_by_xpath('//*[@id="client-searchPane"]/div/input')
    search_input.send_keys(game)
    driver.find_element_by_xpath('//*[@id="event_7388170"]/td/a').click()
    time.sleep(3)
    driver.save_screenshot('betdaq.png')
    

while True:
    
    # create program to ring a bell or create a notification indicating that a team has scored a goal with relevant information
    # save the initial list from start of day of urls to file to check for results at end of day in case network sucks
            
    driver = webdriver.Chrome('chromedriver.exe',options = chrome_options)
    driver.set_window_size(1920, 1080)
            
    # wait for page to load
    ########################## BETDAQ #########################
    # get full time result
    driver.get('https://www.betdaq.com/exchange/soccer/italian-soccer/serie-a/serie-a-matches/18-30-brescia-v-spal-(live)/7394641')
    time.sleep(5)
    driver.save_screenshot('test.png')
            
    image = PIL.Image.open('test.png')

    # MATCH ODDS
    # teams
    image.crop((550,410,800,510)).save('test1.png',quality=100)
    match_odds_teams = pytesseract.image_to_string(cv2.imread('test1.png')).split()
    print(match_odds_teams)

    # home back/lay price/volume
    img = image.resize((220,60),PIL.Image.LANCZOS, (990,410,1100,440)) # upscaled for more accurate opencv reading
    img.save('test1.png',quality=100)
    home_p_v = pytesseract.image_to_string(cv2.imread('test1.png')).split()
    print(home_p_v)

    # draw back/lay price/volume
    img = image.resize((220,60),PIL.Image.LANCZOS, (990,445,1100,480)) # upscaled for more accurate opencv reading
    img.save('test1.png',quality=100)
    draw_p_v = pytesseract.image_to_string(cv2.imread('test1.png')).split()
    print(draw_p_v)

    # away back/lay price/volume
    img = image.resize((220,60),PIL.Image.LANCZOS, (990,480,1100,510)) # upscaled for more accurate opencv reading
    img.save('test1.png',quality=100)
    away_p_v = pytesseract.image_to_string(cv2.imread('test1.png')).split()
    print(away_p_v)
            
            
            
    ############################ SMARKETS #########################
    # do you need to reload the page to see live odd updates 
    driver.get('https://smarkets.com/event/41753532/sport/football/italy-serie-b/2020/07/13/19-00/ascoli-vs-empoli')
    time.sleep(5)
    smarkets_match_outcome = []
    # get full time result
    for i in range(5):
        time.sleep(20)
        for i in range(1,4):
            team = driver.find_element_by_xpath(f"//ul[@class='contract-groups']/li[1]/div/div[2]/div/ul/li[{i}]/div/div/div/span").text # team
            # back
            back_odds = driver.find_element_by_xpath(f"//ul[@class='contract-groups']/li[1]/div/div[2]/div/ul/li[{i}]/div/span[2]/span/span[1]").text # odds
            back_volume = driver.find_element_by_xpath(f"//ul[@class='contract-groups']/li[1]/div/div[2]/div/ul/li[{i}]/div/span[2]/span/span[2]").text # volume
            # lay 
            lay_odds = driver.find_element_by_xpath(f"//ul[@class='contract-groups']/li[1]/div/div[2]/div/ul/li[{i}]/div/span[3]/span/span[1]").text # odds
            lay_volume = driver.find_element_by_xpath(f"//ul[@class='contract-groups']/li[1]/div/div[2]/div/ul/li[{i}]/div/span[3]/span/span[2]").text # volume
            smarkets_match_outcome.append([team, back_odds, back_volume, lay_odds, lay_volume])
                
            print(smarkets_match_outcome)
                
            
        driver.execute_script("window.scrollTo(0, 700)")
        driver.quit()'''
    
