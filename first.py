import grequests
from bs4 import BeautifulSoup
from collections import defaultdict
import pickle
import pandas as pd


LINK_PATTERN = 'https://www.loveandlemons'

batches = 20
url_to_get = 'https://www.loveandlemons.com/recipes/'

page = grequests.get (url_to_get)
response = grequests.map ([page] , size=batches)

soup = [BeautifulSoup (res.text , 'html.parser') for res in response]

recipes_links = [link.get ('href') for link in soup[0].find_all ('a') if
                 str (link.get ('href')).startswith (LINK_PATTERN)]
# print (recipes_links)

json_file = defaultdict (list)

page = (grequests.get (url) for url in set(recipes_links))
response = grequests.map (page , size=batches)
# print (response)
for res in response:
    try:
        soup = BeautifulSoup (res.content , 'html.parser')
    except AttributeError:
        continue
    recipe_ingredients_lines = soup.find_all (attrs={'class': ['wprm-recipe-ingredient' ,
                                                               'ingredient']})
    recipe_instructions_lines = soup.find_all (attrs={'class': ['wprm-recipe-instruction-text' ,
                                                                'instruction']})
    ingredients_list = [item.text for item in recipe_ingredients_lines]
    instructions_list = [paragraph.text for paragraph in recipe_instructions_lines]

    json_file['Recipe'].append (ingredients_list)
    json_file['INSTRUCTIONS'].append (instructions_list)

file = open('new_recipe.pkl', 'wb')
pickle.dump(json_file, file, pickle.HIGHEST_PROTOCOL)
file.close()

df = pd.read_pickle('new_recipe.pkl')
df = pd.DataFrame(df)
df
