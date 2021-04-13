from collections import defaultdict
import grequests
from bs4 import BeautifulSoup
from config import LINK_PATTERN, BATCHES



def get_one(url_to_get):
    """  To collect ingredients and  INSTRUCTIONS text  from a single recipe page
    :param   url_to_get: str,
    :return  json_file: defaultdict('Recipe':list[list[str]], 'INGREDIENTS': list[str]')
    """
    # LINK_PATTERN = 'https://www.loveandlemons'
    # batches = 20
    page = grequests.get (url_to_get)

    response = grequests.map ([page] , size=BATCHES)

    soup = [BeautifulSoup (res.text , 'html.parser') for res in response]

    recipes_links = [link.get('href') for link in soup[0].find_all('a') if
                     str(link.get('href')).startswith(LINK_PATTERN)]
    # print (recipes_links)

    json_file = defaultdict(list)

    page = (grequests.get(url) for url in set(recipes_links))
    response = grequests.map(page, size=BATCHES)
    # print (response)

    # json_file = defaultdict(list)
    # # get data from website
    # page = [grequests.get(url_to_get)]
    # response = grequests.map(page, size=20)
    for res in response:
        try:
            # print (res.content)
            soup = BeautifulSoup(res.content, 'html.parser')
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

        # recipe_ingredients_lines = soup.find_all (attrs={'class': ['wprm-recipe-ingredient' ,
        #                                                            'ingredient']})
        # recipe_instructions_lines = soup.find_all (attrs={'class': ['wprm-recipe-instruction-text' ,
        #                                                             'instruction']})
        # ingredients_list = [item.text for item in recipe_ingredients_lines]
        # instructions_list = [paragraph.text for paragraph in recipe_instructions_lines]
        #
        # # collect data into dictionary
        # json_file['Recipe'].append (ingredients_list)
        # json_file['INSTRUCTIONS'].append ('\n\n'.join (instructions_list))
    return json_file
