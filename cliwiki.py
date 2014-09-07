#! /usr/bin/env python3

""" CLI to access wikipedia informations """

import sys
import os
import json
import urllib.request
import re
import argparse

from collections import OrderedDict
from html.parser import HTMLParser

import urwid


# **** Global Variables ****
BASE_URL = "http://en.wikipedia.org/w/api.php?"
TITLES = ""
RESULT = None
PAGE = None


class ExcerptHTMLParser(HTMLParser):
    sections = OrderedDict({'':[]})
    cursection = ''
    inh2 = False
    inblockquote = False
    bold = False
    italic = False

    def add_text(self, text):
        if self.bold and self.italic:
            tformat = "bolditalic"
        elif self.bold:
            tformat = "bold"
        elif self.italic:
            tformat = "italic"
        else:
            tformat = ''
        if self.inh2:
            self.cursection += text
        elif self.inblockquote:
            self.sections[self.cursection].append((tformat, '> ' + text))
        else:
            self.sections[self.cursection].append((tformat, text))

    def handle_starttag(self, tag, attrs):
        if tag == 'h2':
            self.inh2 = True
            self.cursection = ''
        elif re.fullmatch("h[3-6]", tag):
            self.add_text('\n')
        elif tag == 'i':
            self.italic = True
        elif tag == 'b':
            self.bold = True
        elif tag == 'li':
            self.add_text("- ")
        elif tag == 'blockquote':
            self.inblockquote = True
        else:
            pass

    def handle_endtag(self, tag):
        if tag == 'h2':
            self.inh2 = False
            self.sections[self.cursection] = []
        elif re.fullmatch("h[3-6]", tag):
            self.add_text('\n')
        elif tag == 'i':
            self.italic = False
        elif tag == 'b':
            self.bold = False
        elif tag == 'p':
            self.add_text('\n')
        elif tag == 'blockquote':
            self.inblockquote = False
        else:
            pass

    def handle_data(self, data):
        text = data.replace('*', '\\*')
        text = re.sub('\n+', '\n', text)
        self.add_text(text)

def wiki_query():
    global RESULT
    global PAGE
    data = {"action":"query", "prop":"extracts|info|extlinks|images",
            "titles":TITLES, "redirects":True, "format":"json",
            "inprop":"url|displaytitle"}

    url = BASE_URL + urllib.parse.urlencode(data)
    # open url, read content (bytes), convert in string via decode()
    RESULT = json.loads(urllib.request.urlopen(url).read().decode('utf-8'))
    # In python 3 dict_keys are not indexable, so we need to use list()
    key = list(RESULT['query']['pages'])[0][:]
    PAGE = RESULT['query']['pages'][key]



def wiki_search():
    """ Search function """

    try:
        parser = ExcerptHTMLParser()
        parser.feed(PAGE['extract'])
        parser.sections.pop("External links", '')
        parser.sections.pop("References", '')
        return parser.sections

    except KeyError:
        return {'':'No wikipedia page for that title.\n'
               'Wikipedia search titles are case sensitive.'}



def external_links():
    """ Get external links """

    try:
        offset = RESULT['query-continue']['extlinks']['eloffset']
        output = ''
        for j in range(0, offset):
            # ['*'] => elements of ....[j] are dict, and their keys are '*'
            link = PAGE['extlinks'][j]['*']
            if link.startswith("//"):
                link = "http:" + link
            output += '- <'+link+'>'
        return output
    except KeyError:
        pass



def images():
    """ Get images urls """

    image_url = "http://en.wikipedia.org/wiki/"

    try:
        output = ''
        for i in range(1, len(PAGE['images'])):
            image = PAGE['images'][i]['title']
            image = image_url + image.replace(' ', '_')
            output += '- <'+image+'>'
        return output
    except KeyError:
        pass


def featured_feed(feed):
    """Featured Feed"""

    data = {"action":"featuredfeed", "feed":feed, "format": "json"}
    url = BASE_URL + urllib.parse.urlencode(data)

    result = urllib.request.urlopen(url).read().decode('utf-8')

    re_title = re.compile('<title>(.*)</title>')
    re_links = re.compile('<link>(.*)en</link>')

    result1 = re.findall(re_title, result)
    result2 = re.findall(re_links, result)

    output = '\n'
    for desc, url in zip(result1, result2):
        output += desc + ':\t ' + url
    return output


def interwiki_links():
    """ Inter wiki links """

    output('Inter wiki links found for this search: ')

    url = BASE_URL + ACTION + TITLES + REDIRECTS + "&prop=iwlinks"+ FORMAT

    output(url)

    # TODO: parse the json, match it with a dict containing
    # url to append depending on the key returned in the url,
    # and then only show the resulting urls

    # result = urllib.request.urlopen(url).read().decode('utf-8')

    # for i in reslut:
        # print(i)


def main():
    """ Main function """

    # Gestion des paramètres
    parser = argparse.ArgumentParser(description =
                                        "Access Wikipedia from Command Line")

    parser.add_argument('--nopager',
                        action = 'store_true',
                        help="Do not display using a pager")

    group = parser.add_mutually_exclusive_group(required = True)

    group.add_argument('search',
                        nargs = '?',
                        default = '',
                        help = "Page to search for on Wikipedia")

    group.add_argument('-d', '--today',
                        action = 'store_const',
                        const = 'onthisday',
                        help='Display URLs for the "On this day" pages')

    group.add_argument('-f', '--featured',
                        action = 'store_const',
                        const = 'featured',
                        help = 'Display the featured articles URLs')

    group.add_argument('-p', '--picture',
                        action = 'store_const',
                        const = 'potd',
                        help='Display URLs for the "Picture of the day" pages')


    args = parser.parse_args()

    screen = urwid.raw_display.Screen() 
    screen.register_palette_entry('h1', 'yellow,bold', '')
    screen.register_palette_entry('h2', 'underline', '')
    #screen.register_palette_entry('italic', 'italics', '') #No italics option?
    screen.register_palette_entry('bold', 'bold', '')
    screen.register_palette_entry('bolditalic', 'bold', '')

    widgets = urwid.SimpleFocusListWalker([])


    if args.search :
        global TITLES
        TITLES = args.search
        wiki_query()
        sections = wiki_search()
        imgurls = images()
        links = external_links()
        # interwiki_links()

        widgets.append(urwid.Text(('h1', PAGE['title']), align="center"))

        for i in sections:
            if i:
                widgets.append(urwid.Text(('h2', i), align="center"))
            widgets.append(urwid.Text(sections[i]))
        if imgurls:
            widgets.append(urwid.Text(('h2', 'Images\n'), align="center"))
            widgets.append(urwid.Text(imgurls))
        if links:
            widgets.append(urwid.Text(('h2', '\nExternal links\n'), align="center"))
            widgets.append(urwid.Text(links))

    elif args.featured:
        widgets.append(urwid.Text(('h1', "Featured Articles"), align="center"))
        widgets.append(urwid.Text(featured_feed(args.featured)))

    elif args.picture:
        widgets.append(urwid.Text(('h1', "Picture of the Day"), align="center"))
        widgets.append(urwid.Text(featured_feed(args.picture)))

    elif args.today:
        widgets.append(urwid.Text(('h1', "On this Day"), align="center"))
        widgets.append(urwid.Text(featured_feed(args.today)))


    pager = urwid.ListBox(widgets)
    pager._command_map['k'] = 'cursor up'
    pager._command_map['j'] = 'cursor down'
    pager._command_map['ctrl b'] = 'cursor page up'
    pager._command_map['ctrl f'] = 'cursor page down'

    loop = urwid.MainLoop(pager,screen=screen)
    def keymapper(input):
        #TODO: Implement gg and G
        if input == 'q':
            raise  urwid.ExitMainLoop
        else:
            return False
        return True
    loop.unhandled_input = keymapper
    loop.run()


if __name__ == "__main__":
    main()
