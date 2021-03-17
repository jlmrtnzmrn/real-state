# -*- coding: utf-8 -*-
import webarchive
import glob
import selenium
from bs4 import BeautifulSoup as soup
import numpy as np
import re
import argparse
import random


def getPrice(det_html):
  precio = int(det_html.find('span', {'class':'info-data-price'}).text.strip(' €').replace('.',''))

  if det_html.find('span', {'class':'pricedown_price'}) == None:
      precio_original = precio
  else:
      precio_original = det_html.find('span', {'class':'pricedown_price'}).text.strip('\n').strip(' €').replace('.','')

  return [precio, precio_original]

def pictures(det_html):
  if det_html.find('span', {'class':'fa-button-text'}) == None:
    fotos = 0
  else:
    fotos = int(det_html.find('span', {'class':'fa-button-text'}).text.replace(' fotos',''))
  return fotos

def getUrl(det_html):
  urls = det_html.find("a", {'class': re.compile(r"main*")}, href=re.compile(r"^https://www.idealista.com/inmueble/*"))
  return urls.get('href')

def getId(det_html):
  return getUrl(det_html).split('/')[-2]

def anunciante(det_html):
  anunciante = []
  if len(det_html.find_all('div',{'class':'advertiser-name-container'}))==0:
      anunciante = ['Particular '+ det_html.find_all('span',{'class':'particular'})[0].text.replace('\n','')]
  else:
      for i in det_html.find_all('div',{'class':'advertiser-name-container'})[0].text.split('\n'):
          if i != '':
              anunciante.append(i)
  anunciante = anunciante[0]
  if 'Particular' not in anunciante:
    anunciante = 'Inmobiliaria ' + anunciante
  return anunciante

def comment(det_html):
  return det_html.find('div', {'class':'adCommentsLanguage expandable'}).find_all('p')[0].text

def getName(det_html):
  return det_html.find('span', {'class':'main-info__title-main'}).text

def getGeneral(det_html):
  section = det_html.find('div', {'class':'info-features'}).find_all('span')
  #print(section)
  features = []
  for span in section:
    text = span.get_text().replace('\n', ' ')
    features.append(text.strip())
  return features[0::2]

def getFeatures(det_html):
  section = det_html.find('section', {'id':'details'}).select('div[class*="detail"]')
  #print(section)
  features = []
  for div in section:
    text = div.get_text().split('\n')
    for item in text:
      if len(item)>0:
        if "orienta" in item.lower():
          features += [item]
        else:
          features += item.split(',')
  features = [item.strip() for item in features]
  return list(np.unique(features))

def update(det_html):
  act = det_html.find_all('div',{'class':'ide-box-detail overlay-box mb-jumbo'})[0].find('p').text
  return act

def direction(det_html):
  direccion = []
  for i in det_html.find_all('div',{'id':'headerMap'})[0].text.split('\n'):
      if i != '' and 'Ubicación' not in i:
          direccion.append(i)
  return direccion

"""
||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
"""

def process_features(list_, det_html):
  list_ = list(np.unique(list_))
  #print(list_)
  def remove(list_, items):
    for item in items:
      list_.remove(item)
    return list_

  def checkEmpty(list_):
    newlist = []
    if len(list_)==0:
      newlist.append(None)
      return newlist
    else:
      return list_

  def str2list(list_):
    newlist = []
    for item in list_:
      newlist += item.split(',')
    newlist = [item.strip() for item in newlist]
    return newlist

  def flatten_list(_2d_list):
    flat_list = []
    # Iterate through the outer list
    for element in _2d_list:
        if type(element) is list:
            # If the element is of type list, iterate through the sublist
            for item in element:
                flat_list.append(item)
        else:
            flat_list.append(element)
    return flat_list

  def get_number(str_):
    str_ = str(str_)
    try:
      return re.findall(r'\d+', str_)[0]
    except:
      return None


  def get_hab(list_):
    newlist = [i for i in list_ if re.search(r'hab.|habitaciones', i.lower()) ]
    return {'n_hab': get_number(newlist[-1]), 'remove': newlist}

  def get_bano(list_):
    newlist = [i for i in list_ if re.search(r'baños', i.lower()) ]
    return {'n_banos': get_number(newlist[-1]), 'remove': newlist}

  def get_m2(list_):
    #list_ = str2list(list_)
    newlist = [i for i in list_ if re.search(r'm²', i.lower()) ]
    construidos = [i for i in newlist if re.search(r'constru', i.lower()) ]
    utiles = [i for i in newlist if re.search(r'tiles', i.lower()) ]

    for item in list(np.unique(construidos+utiles)):
      newlist.remove(item)
    other = newlist
    flat_remove = flatten_list(construidos+utiles+other)

    return {'m2_construidos': get_number(checkEmpty(construidos)[-1]), 'm2_utiles': get_number(checkEmpty(utiles)[-1]), 'm2_other': checkEmpty(other), 'remove': flat_remove}

  def get_garaje(list_):
    newlist = [i for i in list_ if re.search(r'garaje', i.lower()) ]
    price = 0
    garaje = False
    if len(newlist)>0:
      garaje=True
      if '€' in newlist[-1]:
        price = re.match(r'\d+(?:,\d+)?', newlist[-1])

    return {'garaje': garaje, 'garaje_cost': price, 'remove': newlist}

  def get_ascensor(list_):
    ascensor = None
    newlist1 = [i for i in list_ if re.search(r'con ascensor', i.lower()) ]
    if len(newlist1)>0:
      ascensor = True
    newlist2 = [i for i in list_ if re.search(r'sin ascensor', i.lower()) ]
    if len(newlist2)>0:
      ascensor = False
    return {'ascensor':  ascensor, 'remove': newlist1+newlist2}

  def get_aire(list_):
    newlist = [i for i in list_ if re.search(r'aire', i.lower()) ]
    aire = False
    if len(newlist)>0:
      aire = True
    return {'aire_acondicionado': aire, 'remove': newlist}

  def get_planta(list_):
    newlist = [i for i in list_ if re.search(r'planta', i.lower()) ]
    planta = None
    if len(newlist)>0:
      planta = get_number(newlist[-1])

    newlist2 = [i for i in list_ if re.search(r'bajo', i.lower()) ]
    if len(newlist2)>0:
      if planta is None:
        planta = 'bajo'
      else:
        planta = f'bajo ? {planta}?'

    return {'planta': planta, 'remove': newlist+newlist2}

  def get_extint(list_):
    newlist1 = [i for i in list_ if re.search(r'exterior', i.lower()) ]
    newlist2 = [i for i in list_ if re.search(r'interior', i.lower()) ]
    intext = ''
    if len(newlist1)>0:
      intext = 'exterior'
    if len(newlist2)>0:
      intext += 'interior'
    if len(intext)==0:
      intext = None
    return {'intext': intext, 'remove': newlist1+newlist2}

  def get_calefa(list_):
    newlist = [i for i in list_ if re.search(r'calefa', i.lower()) ]
    var1 = None
    var2 = None
    if len(newlist)>0:
      var1 = newlist[-1].split()[1].strip().lower()
      var2 = checkEmpty(newlist[-1].split(":"))[-1].strip().lower()

    return {'calefaccion': (var1, var2), 'remove': newlist}

  def get_ce(list_):
    newlist = [i for i in list_ if re.search(r'certifica', i.lower()) ]
    ce = None
    if len(newlist)>0:
      ce = newlist[-1].split(':')[-1].strip().lower()
    return {'ce': ce, 'remove': newlist}


  def get_year(list_):
    newlist = [i for i in list_ if re.search(r'construido en', i.lower()) ]
    year = None
    if len(newlist)>0:
      year = get_number(newlist[-1])
    return {'year': year, 'remove': newlist}

  # completar
  def get_estado(list_):
    estados = ['obra', 'segunda', 'reform' ]
    lists = []
    var = ''
    for item in estados:
      lists.append([i for i in list_ if re.search(r'{}'.format(item), i.lower()) ])
    for item in lists:
      if len(item)>0:
        var = var + item[-1]
    if len(var)==0:
      var = None
    return {'estado': var, 'remove': flatten_list(lists)}




    #newlist = [i for i in list_ if re.search(r'estado', i.lower()) ]
    #return {'estado': checkEmpty(newlist)[-1], 'remove': newlist}

  def get_orientation(list_):
    newlist = [i for i in list_ if re.search(r'orienta', i.lower()) ]

    if len(newlist)>0:
      orientation = "".join(checkEmpty(newlist)[-1].split()[1:]).replace(',', '-')
    else:
      orientation = None


    return {'orientacion': orientation , 'remove': newlist}

  def get_piscina(list_):
    newlist = [i for i in list_ if re.search(r'piscina', i.lower()) ]
    piwi = None
    if len(newlist)>0:
      piwi= True
    return {'piwi': piwi, 'remove': newlist}

  def get_movilidad(list_):
    newlist = [i for i in list_ if re.search(r'movilidad reducida', i.lower()) ]
    mov = None
    if len(newlist)>0:
      mov= True
    return {'movilidad_reducida': mov, 'remove': newlist}

  def get_jardin(list_):
    newlist = [i for i in list_ if re.search(r'jard', i.lower()) ]
    jardin = None
    if len(newlist)>0:
      jardin= True
    return {'jardin': jardin, 'remove': newlist}

  def get_tipo(list_, det_html):
    tipo = ['piso', 'casa', 'plex', 'tico', 'chalet']
    lists = []
    list_var = []
    var = ''
    for item in tipo:
      lists.append([i for i in list_ if re.search(r'{}'.format(item), i.lower()) ])
    for item in lists:
      if len(item)>0:
        list_var.append(item[-1])
        x = list(np.unique(list_var))
    if len(x)>0:
      for item in x:
        var = var + item
    if len(var)==0:
      name = getName(det_html)
      print(name, 'here')
      for item in tipo:
        if item in name.lower():
          var = var + name.split()[0].lower()
    if len(var)==0:
      var = None
    return {'tipo': var, 'remove': flatten_list(lists)}

  def get_balcon(list_):
    newlist = [i for i in list_ if re.search(r'balc', i.lower()) ]
    balcon = None
    if len(newlist)>0:
      balcon= True
    return {'balcon': balcon, 'remove': newlist}

  def get_armarios(list_):
    newlist = [i for i in list_ if re.search(r'armarios', i.lower()) ]
    var = None
    if len(newlist)>0:
      var= True
    return {'armarios_empotrados': var, 'remove': newlist}

  def get_trastero(list_):
    newlist = [i for i in list_ if re.search(r'trastero', i.lower()) ]
    var = None
    if len(newlist)>0:
      var= True
    return {'trastero': var, 'remove': newlist}

  def get_terraza(list_):
    newlist = [i for i in list_ if re.search(r'terraza', i.lower()) ]
    var = None
    if len(newlist)>0:
      var= True
    return {'terraza': var, 'remove': newlist}

  def get_luxury(list_):
    newlist = [i for i in list_ if re.search(r'lujo', i.lower()) ]
    var = None
    if len(newlist)>0:
      var= True
    return {'lujo': var, 'remove': newlist}

  hab = get_hab(list_)
  banos = get_bano(list_)
  m2 = get_m2(list_)
  garaje = get_garaje(list_)
  aire = get_aire(list_)
  ascensor = get_ascensor(list_)
  planta = get_planta(list_)
  intext = get_extint(list_)
  calefa = get_calefa(list_)
  ce = get_ce(list_)
  year = get_year(list_)
  estado = get_estado(list_)
  orientacion = get_orientation(list_)
  piwi = get_piscina(list_)
  mov = get_movilidad(list_)
  jardin = get_jardin(list_)
  tipo = get_tipo(list_, det_html)
  balcon = get_balcon(list_)
  armarios = get_armarios(list_)
  trastero = get_trastero(list_)
  terraza = get_terraza(list_)
  lujo = get_luxury(list_)

  dict_list = [hab, banos,
              m2, garaje,
              aire, ascensor,
              planta, intext,
              calefa, ce,
              year, estado,
              orientacion, piwi,
              mov, jardin,
              tipo, balcon,
              terraza, trastero,
              armarios, lujo]
  res = {}
  for dict_ in dict_list:
      for item in dict_:
        if item in res:
            res[item] += (dict_[item])
        else:
            res[item] = dict_[item]


  return res
  #list_ = remove(list_, hab+banos+flat_m2)
  #print(list_)
  #return [hab[-1], banos[-1], m2] + list_


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='idealista')
  parser.add_argument('--file', type=int, default=0,
                      help='an integer for the accumulator')


  args = parser.parse_args()

  path = '/Users/drsitxu/Downloads/idealista/done'

  files = glob.glob(path + '/*.webarchive')

  file = files[args.file]

  print(file)
  archive = webarchive.open(file)
  archive.extract('file.html')

  det_html = soup(open('file.html'), features="lxml")

  features = getFeatures(det_html)
  anunciante = anunciante(det_html)
  direccion= direction(det_html)
  act= update(det_html)
  url = getUrl(det_html)
  id_ = getId(det_html)
  comentario= comment(det_html)
  fotos = pictures(det_html)
  nombre = getName(det_html)
  general = getGeneral(det_html)
  precio = getPrice(det_html)

  all_genfet = general+features
  print('all', all_genfet)
  res = process_features(all_genfet, det_html)

  for item in list(np.unique(res['remove'])):
    all_genfet.remove(item)

  outputs = {
    "nombre": nombre,
    "url": url,
    "id": id_,
    "precio": precio[0],
    "precio_original": precio[1],
    "año": res['year'],
    "n_fotos": fotos,
    #'general': general,
    'features': all_genfet,
    "n_habitaciones": res['n_hab'],
    "n_banos:": res['n_banos'],
    "calefaccion": res['calefaccion'],
    "estado": res['estado'],
    #"exterior": exterior,
    "certificacion_energetica": res['ce'],
    'planta': res['planta'],
    'int/ext': res['intext'],
    "ascensor" : res['ascensor'],
    "garaje" : [res['garaje'], res['garaje_cost']],
    "aire_acondicionado": res['aire_acondicionado'],
    "m2_cons" : res['m2_construidos'],
    "m2_util" : res['m2_utiles'],
    'm2_other': res['m2_other'],
    "actualizacion": act,
    'piscina': res['piwi'],
    'movilidad_reducida': res['movilidad_reducida'],
    'orientacion': res['orientacion'],
    'jardin': res['jardin'],
    'tipo': res['tipo'],
    'balcon': res['balcon'],
    'armarios_empotrados': res['armarios_empotrados'],
    'terraza': res['terraza'],
    'trastero': res['trastero'],
    'lujo': res['lujo'],
    #"other1" : car_bas,
  #"other2": car_eq,
  #"planta": planta,

  "direccion":direccion,
  "anunciante": anunciante,
  "comentario": comentario

  }

  for key, value in outputs.items():
    print(key, ': ', value)

  # SIMULATION
  if False:
    total = []
    for i, file in enumerate(random.sample(files,100)):
      if i%10==0:
        print(i)

      archive = webarchive.open(file)
      archive.extract('file.html')

      det_html = soup(open('file.html'), features="lxml")
      features = getFeatures(det_html)
      general = getGeneral(det_html)
      total = total + features+general


    #print(total)
    vars_ = ['armarios', 'terraza', 'trastero', 'bajo', 'banco']

    for var in vars_:
      with open(f'{var}.txt', 'w') as file:
            file.write('Start'+'\n')

    for item in total:
      for var in vars_:
        if f'{var}' in item.lower():
          with open(f'{var}.txt', 'a') as file:
            file.write(item+'\n')
