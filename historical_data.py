# loop through each folder in historical data:
# - extract all the bzp files
# - loop through the extracted files and look for 'OVER_UNDER_05'
# - if file contains 'OVER_UNDER_05' get 'marketTime' and 'settledTime' to see how long it takes on average for first goal to be scored
# then look for average price movement of over/under 0.5

import os, bz2

no_events = 0
fails = 0
root = 'C:\\Users\\Case\\Documents\\Code\\sports_trading\\data\\BASIC'
root_one = os.listdir(root)

for i in root_one: # get months
    root_two = os.listdir(root+'\\'+i)
    print(root_two)
    
    for x in root_two: # get days
        root_three = os.listdir(root+'\\'+i+'\\'+x)
        print('\n')
        print(root_three)
        
        for z in root_three: # get events per day
            root_four = os.listdir(root+'\\'+i+'\\'+x+'\\'+z)
            print(root_four)
            
            
            for s in root_four: # get data files for event
                root_five = os.listdir(root+'\\'+i+'\\'+x+'\\'+z+'\\'+s)
                print(root_five)
                no_events+=1
                
                for file in root_five[:len(root_five)-1]: # last file contains all the data for that event, which would mean two occurences of each below
                    if '.bz2' in file:
                        with bz2.open(root+'\\'+i+'\\'+x+'\\'+z+'\\'+s+'\\'+file, mode='r') as f:
                            data = f.read().decode()
                            if 'OVER_UNDER_05' in data:
                                print('\n'+root+'\\'+i+'\\'+x+'\\'+z+'\\'+s+'\\'+file)
                                
                                try:
                                    print('Lost: '+data[data.index('LOSER')+45:data.index('LOSER')+60])
                                    print(data[data.index('marketTime'):data.index('marketTime')+38])
                                    print(data[data.index('settledTime'):data.index('settledTime')+39])
                                    zero_five_goals = [(data[data.index('marketTime'):data.index('marketTime')+38])[24:29],
                                                        (data[data.index('settledTime'):data.index('settledTime')+39])[25:30]]       
                                    print(zero_five_goals)
                                except Exception as e:
                                    print(e)
                                    
                                    
                            if 'OVER_UNDER_15' in data:
                                print('\n'+root+'\\'+i+'\\'+x+'\\'+z+'\\'+s+'\\'+file)
                                
                                try:
                                    print('Lost: '+data[data.index('LOSER')+45:data.index('LOSER')+60])
                                    print(data[data.index('marketTime'):data.index('marketTime')+38])
                                    print(data[data.index('settledTime'):data.index('settledTime')+39])
                                    # [game start time, settled time]
                                    one_five_goals = [(data[data.index('marketTime'):data.index('marketTime')+38])[24:29],
                                                        (data[data.index('settledTime'):data.index('settledTime')+39])[25:30]]
                                    print(one_five_goals)
                                except Exception as e:
                                    print(e)
                                    
                            
                            if 'OVER_UNDER_25' in data:
                                print('\n'+root+'\\'+i+'\\'+x+'\\'+z+'\\'+s+'\\'+file)
                                
                                try:
                                    print('Lost: '+data[data.index('LOSER')+43:data.index('LOSER')+58])
                                    print(data[data.index('marketTime'):data.index('marketTime')+38])
                                    print(data[data.index('settledTime'):data.index('settledTime')+39])
                                    # [game start time, settled time]
                                    two_five_goals = [(data[data.index('marketTime'):data.index('marketTime')+38])[24:29],
                                                        (data[data.index('settledTime'):data.index('settledTime')+39])[25:30]]
                                    print(two_five_goals)
                                except Exception as e:
                                    print(e)
                                # include the event - possible weird times are because of unmanaged games. european leagues tend to be managed
                                
                            if 'OVER_UNDER_35' in data:
                                print('\n'+root+'\\'+i+'\\'+x+'\\'+z+'\\'+s+'\\'+file)
                                
                                try:
                                    print('Lost: '+data[data.index('LOSER')+43:data.index('LOSER')+58])
                                    print(data[data.index('marketTime'):data.index('marketTime')+38])
                                    print(data[data.index('settledTime'):data.index('settledTime')+39])
                                    # [game start time, settled time]
                                    three_five_goals = [(data[data.index('marketTime'):data.index('marketTime')+38])[24:29],
                                                        (data[data.index('settledTime'):data.index('settledTime')+39])[25:30]]
                                    print(three_five_goals)
                                except Exception as e:
                                    print(e)
                                    
                            if 'OVER_UNDER_45' in data:
                                print('\n'+root+'\\'+i+'\\'+x+'\\'+z+'\\'+s+'\\'+file)
                                
                                try:
                                    print('Lost: '+data[data.index('LOSER')+43:data.index('LOSER')+58])
                                    print(data[data.index('marketTime'):data.index('marketTime')+38])
                                    print(data[data.index('settledTime'):data.index('settledTime')+39])
                                    # [game start time, settled time]
                                    four_five_goals = [(data[data.index('marketTime'):data.index('marketTime')+38])[24:29],
                                                        (data[data.index('settledTime'):data.index('settledTime')+39])[25:30]]
                                    print(four_five_goals)
                                except Exception as e:
                                    print(e)
                                    
                                
                # TODO 2300H + 1 should be 0000H not 2400H
                # TODO don't count event if over 2.5 goals won before half time, because trade wouldn't be taken
                # TODO consider extra time before first half
                # TODO what is 'substring not found' - is it considered as fail?
                # TODO what about games that seem to settle hours after the game should have ended?
                # TODO fix going back through jan again after already having the data??
                try:
                    goals = [zero_five_goals, one_five_goals, two_five_goals, three_five_goals, four_five_goals]
                    for c,time in enumerate(goals):
                        if int(time[0][:2])+1 == int(time[1][:2]): # if 1 hour difference between start of game and goal -> 45' + 15' HT
                            if int(time[1][3:]) in range(int(time[0][3:]), int(time[0][3:])+6): # if goal within 10 min of second half
                                
                                if c >= 3: # 4-5 goals scored
                                    no_events-=1 # won't be taking trade if 3 goals scored before 1st half so don't count it as a 'won' trade
                                    break
                                
                                print('goal scored 10-15 minutes after half time',time)
                                fails+=1    
                                break # eg. if 0.5 goal occurs, don't count 1.5 goal as another fail, because would have gotten out of trade already
                except Exception as e:
                    print(e)
                    
print(no_events,fails)