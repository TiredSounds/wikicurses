import re

from collections import OrderedDict
from bs4 import BeautifulSoup

from wikicurses import formats

class UrwidMarkupHandler:
    def __init__(self):
        self._list = []

    def add(self, text, attribute):
        if self and self[-1][0] == attribute:
            self[-1][1] += text
        else:
            self._list.append([attribute, text])

    def __iter__(self):
        return map(tuple, self._list)

    def __len__(self):
        return len(self._list)

    def __getitem__(self, key):
        return self._list[key]

def _processExtractSection(section):
    items = UrwidMarkupHandler()
    for i in section:
        if isinstance(i, str):
            strings = (i,)
        else: 
            if i.name == 'h2' or i.find('h2'):
                break
            strings = i.strings
        for item in strings:
            if [i for i in item.parents if i.name == 'table'\
                    and {'wiki-sidebar', 'infobox'}.intersection(i.get('class', ()))]:
                continue
            partags = {i.name for i in item.parents}
            format = sum(formats[i] for i in set(i.name for i in formats).intersection(partags))
            if [i for i in partags if re.fullmatch('h[3-6]', i)]:
                format = 'h'
                item = re.sub('\[edit\]$', '', item)
                item = re.sub('Edit$', '', item)
            items.add(item, format)
    if items and items[-1]:
        items[-1][1] = items[-1][1].rstrip() + '\n'
    return items

def parseExtract(html):
    html = re.sub('\n+', '\n', html).replace('\t', ' ')
    sections = OrderedDict()
    soup = BeautifulSoup(html)
    for i in soup.find_all(['p', 'br', 'h3', 'h4', 'h5', 'h6']):
        i.insert_after(soup.new_string('\n'))
    for i in soup.find_all('li'):
        i.insert_before(soup.new_string('- '))
    sections[''] = _processExtractSection(soup)
    for i in soup.find_all('h2'):
        title = re.sub('\[edit\]$', '', i.text)
        title = re.sub('Edit$', '', title)
        if title not in ('Contents', 'External links', 'References'):
            sections[title.strip()] = _processExtractSection(i.next_siblings)
    for i in sections:
        if not sections[i]:
            del sections[i]
    return sections

def parseFeature(html):
    return BeautifulSoup(html).text

def _processDisambigSection(section):
    items = []
    for i in section:
        if isinstance(i, str):
            continue
        if i.name == 'h2' or i.find('h2'):
            break
        for item in i.find_all('li'):
            items.append((item.a.text if item.a else '', item.text.split('\n')[0]))
    return items

def parseDisambig(html):
    sections = OrderedDict()
    soup = BeautifulSoup(html)
    sections[''] = _processDisambigSection(soup)
    for i in soup.find_all('h2'):
        title = re.sub('\[edit\]$', '', i.text)
        title = re.sub('Edit$', '', title)
        if title not in ('Contents', 'See also'):
            sections[title] = _processDisambigSection(i.next_siblings)
    return sections
