import csv
import os
import random
import re
import sys
import time
from datetime import datetime
from random import choice
import pandas
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from match import Match
from team import Team


def set_profile(useragent, proxy):
    profile = webdriver.FirefoxProfile()
    profile.set_preference("general.useragent.override", useragent)
    profile.set_preference("network.proxy.type", 1)
    profile.set_preference("network.proxy.http", proxy[0])
    profile.set_preference("network.proxy.http_port", int(proxy[1]))
    profile.update_preferences()
    return profile

def parse(url, sport=None, profile=None, file_path=None):
    while True:
        driver = None
        try:
            driver = webdriver.Firefox(firefox_profile=profile)
            driver.implicitly_wait(5)
            driver.get(url)
            sport = sport or "soccer"
            driver.find_element_by_class_name(sport).click()
            WebDriverWait(driver, timeout=30).until(
                lambda x: x.find_element_by_class_name("table-main"))
            parent_window = driver.current_window_handle
            pattern = re.compile("^.*(Cup|Copa|Кубок|кубок).*$")
            for index, league in enumerate(driver.find_elements_by_class_name("head_ab")):
                os.system('cls')
                league_name = league.find_element_by_class_name(
                    "name").text.strip()
                if league.find_element_by_tag_name('span').text == "Таблица" and pattern.search(league_name) == None:
                    os.system("cls")
                    print("\n\nLeague : " + league_name + '\n\n')
                    league.find_element_by_tag_name('span').click()
                    league_results(url, driver, sport, league_name, index)
                    driver.switch_to_window(parent_window)
            driver.close()
        except TimeoutError:
            print("=========Timeout error=========")
            if driver != None:
                if isinstance(driver.webdriver.Firefox):
                    driver.close()
            continue
        except OSError as e:
            print(e)
            print("=======Waiting...=======")
            if driver != None:
                if isinstance(driver.webdriver):
                    driver.close()
            continue
        else:
            driver.quit()
            break


def league_results(url, driver, sport, league_name, index):
    link_pattern = re.compile(".*\('(.+)'\);")
    parent_window = driver.current_window_handle
    file_name = "leagues/league-{}.csv".format(index + 1)
    with open(file_name, 'a', encoding="utf-8", newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(('Вид спорта', 'Лига', 'Команда',	'Матч',	'Дата', 'Итог',	'Счёт', 'Чёт/нечет', 'Тотал', 'Инд.тотал команды',
                        'Инд. чёт/ нечет', 'Тотал б/м [тотал]', 'Инд.тотал б/м [тотал]', 'Дом / Выезд', 'Овертайм', 'След. матч', 'Соперник'))
        for handle in driver.window_handles:
            if handle != parent_window:
                driver.switch_to_window(handle)
                WebDriverWait(driver, timeout=10).until(
                    lambda x: x.find_element_by_class_name("glib-stats-data"))
                # команды
                for span in driver.find_elements_by_class_name("team_name_span"):
                    team_name = span.find_element_by_tag_name(
                        "a").text.strip()  # ?
                    onclick = span.find_element_by_tag_name(
                        "a").get_attribute("onclick")
                    link = link_pattern.search(onclick).group(1)
                    print("\nTeam : " + team_name + '\n')
                    current_window = driver.current_window_handle
                    driver.switch_to_window(parent_window)
                    driver.execute_script("window.open();")
                    tab_handle = None
                    for index, handle in enumerate(driver.window_handles):
                        if index == 1:
                            tab_handle = handle
                            driver.switch_to_window(handle)
                            driver.get(url+link+'results')
                            break
                    driver.switch_to_window(tab_handle)
                    next_ = str(url+link)
                    team = parse_football_team(
                        sport, league_name, team_name, driver, next_)
                    write_team(writer, team)
                    driver.close()
                    driver.switch_to_window(current_window)
                driver.close()

def parse_football_team(sports, league_name, team_name, driver):
    team = Team(sports, league_name, team_name)
    WebDriverWait(driver, timeout=30).until(
        lambda x: x.find_element_by_id("fs-results"))
    soup = BeautifulSoup(driver.page_source, 'lxml')
    div = soup.find('div', id='fs-results')
    flag = False
    match_count = 0
    for tbody in div.find_all("tbody"):
        if flag == True:
            break
        for tr in tbody.find_all("tr"):
            match_count += 1
            if match_count > 15:
                flag = True
                break
            place = "дом"
            date = tr.find('td', class_='time').text.split()[0]
            team_self = tr.find('td', class_='team-home').text
            team_rival = tr.find('td', class_='team-away').text
            td_score = tr.find('td', class_='score')
            if len(td_score.contents) > 1:   # если есть доп время или пенальти
                self_score = int(td_score.contents[0].split(':')[0].strip())
                rival_score = int(td_score.contents[0].split(':')[1].strip())
                aet = td_score.find('span', class_='aet').text.strip()
                pat = re.compile("^\((.+)\)$")
                sc = pat.search(aet).group(1).strip().split(':')
                maintime = {
                    'home-score': int(sc[0].strip()), 'guest-score': int(sc[1].strip())}
            else:
                self_score = int(
                    tr.find('td', class_='score').text.split(':')[0].strip())
                rival_score = int(
                    tr.find('td', class_='score').text.split(':')[1].strip())
                maintime = None
            if re.search(team_name, team_rival):
                team_rival = team_self
                self_score, rival_score = rival_score, self_score
                if maintime:
                    maintime['home-score'], maintime['guest-score'] = maintime['guest-score'], maintime['home-score']
                place = "выезд"
            team.matches.append(
                Match(date, team_name, team_rival, self_score, rival_score, place, maintime))
    return team

def write_team(writer, team):
    for match in team.matches:
        writer.writerow((team.sport, team.league, team.name, match.rival, match.date, match.result(), match.match_score(), match.odd_even(
        ), match.total(), match.score, match.ind_odd_even(), '-', '-', match.place, match.overtime(), team.next['date'], team.next['rival']))

def write_to_excel(directory):
    excel_file = 'leagues/football.xlsx'
    excel_writer = pandas.ExcelWriter(excel_file, engine='xlsxwriter')
    for index, file_name in enumerate(os.listdir(directory)):
        f_name = "leagues/{}".format(file_name)
        df = pandas.read_csv(f_name, sep=',', keep_default_na=False)
        sheet = "Sheet-{}".format(index + 1)
        print(df['Тотал'])
        df.to_excel(excel_writer, sheet_name=sheet)
    workbook = excel_writer.book
    add_color_format(workbook)
    excel_writer.save()

def main():
    useragents = open('agents.txt').read().split('\n')
    proxies = open('proxies.txt').read().split('\n')
    useragent = choice(useragents)
    proxy = choice(proxies).split(":")
    profile = set_profile(useragent, proxy)
    parse("url", profile)

def agents_from(url=None):
    attempt = 1
    while True:
        try:
            url = "https://developers.whatismybrowser.com/useragents/explore/software_name/firefox/"
            driver = webdriver.Firefox()
            driver.get(url)
            with open('agents.txt', 'w', encoding='utf-8') as f:

                for i in range(10, 20):
                    driver.get(url + "%d" %
                               i + "?order_by=-operating_system_name")
                    soup = BeautifulSoup(driver.page_source, 'lxml')
                    for agent in soup.find_all('td', class_='useragent'):
                        f.write(agent.a.text + '\n')
        except OSError:
            os.system('cls')
            attempt += 1
            continue
        else:
            driver.close()
            break

def add_color_format(workbook, total=2.5, ind_total=1.5):
    print("From add_color_format()")
    total = 2.5
    ind_total = 1.5
    t_more = workbook.add_format(
        {'bg_color': "#ffdd03", 'align': 'center'})  # t more
    t_less = workbook.add_format(
        {'bg_color': "#2bafe3", 'align': 'center'})  # t less
    victory = workbook.add_format(
        {'bg_color': "#2ab53a", 'align': 'center'})  # victory
    draw = workbook.add_format(
        {'bg_color': "#ffe62b", 'align': 'center'})  # draw
    loss = workbook.add_format(
        {'bg_color': "#ff301a", 'align': 'center'})  # loss
    odd = workbook.add_format(
        {'bg_color': "#ff6352", 'align': 'center'})  # odd
    even = workbook.add_format(
        {'bg_color': "#42c6ff", 'align': 'center'})  # even
    ind_more = workbook.add_format(
        {'bg_color': "#558552", 'align': 'center'})  # ind t more
    ind_less = workbook.add_format(
        {'bg_color': "#f0c0a1", 'align': 'center'})  # ind t less
    home = workbook.add_format(
        {'bg_color': "#ff5ce4", 'align': 'center'})  # home
    guest = workbook.add_format(
        {'bg_color': "#7746e0", 'align': 'center'})  # guest
    others = workbook.add_format(
        {'bg_color': "#bae3f5", 'align': 'center', 'border': 2})  # other cells
    header = workbook.add_format(
        {'bg_color': "white", 'align': 'center', 'bold': 'true'})
    numeric = workbook.add_format(
        {'bg_color': "#bae3f5", 'align': 'center', 'border': 2})
    # numeric.set_num_format(1)
    for worksheet in workbook.worksheets():
        worksheet.set_column('H:H', 14, others)
        worksheet.set_column('Q:Q', 15, others)
        worksheet.set_column('R:R', 25, others)
        worksheet.set_column('C:C', 40, others)
        worksheet.set_column('D:E', 25, others)
        worksheet.set_column('B:B', 15, others)
        worksheet.set_column('F:F', 10, others)
        worksheet.set_column('L:L', 15, others)
        worksheet.set_column('P:P', 10, others)
        worksheet.set_column('G:G', 14, others)
        worksheet.set_column('I:I', 14, others)
        worksheet.set_column('O:O', 14, others)
        worksheet.set_column('J:J', 15, others)
        worksheet.set_column('K:K', 20, others)
        worksheet.set_column('M:M', 20, others)
        worksheet.set_column('N:N', 21, others)
        worksheet.write('M1', 'Тотал б/м [{}]'.format(total), header)
        worksheet.write('N1', 'Инд.Тотал б/м [{}]'.format(ind_total), header)
        worksheet.conditional_format('M2:M1000', {
                                     'type': 'formula', 'criteria': "=$J2>{}".format(total), 'format': t_more})
        worksheet.conditional_format('M2:M1000', {
                                     'type': 'formula', 'criteria': "=$J2<{}".format(total), 'format': t_less})
        worksheet.conditional_format('N2:N1000', {
                                     'type': 'formula', 'criteria': "=$K2>{}".format(ind_total), 'format': ind_more})
        worksheet.conditional_format('N2:N1000', {
                                     'type': 'formula', 'criteria': "=$K2<{}".format(ind_total), 'format': ind_less})
        worksheet.conditional_format('I2:I1000', {
                                     'type': 'text', 'criteria': 'containing', 'value': "Чёт", 'format': even})
        worksheet.conditional_format('I2:I1000', {
                                     'type': 'text', 'criteria': 'containing', 'value': "Нечет", 'format': odd})
        worksheet.conditional_format('L2:L1000', {
                                     'type': 'text', 'criteria': 'containing', 'value': "Чёт", 'format': even})
        worksheet.conditional_format('L2:L1000', {
                                     'type': 'text', 'criteria': 'containing', 'value': "Нечет", 'format': odd})
        worksheet.conditional_format('G2:G1000', {
                                     'type': 'text', 'criteria': 'containing', 'value': "Победа", 'format': victory})
        worksheet.conditional_format('G2:G1000', {
                                     'type': 'text', 'criteria': 'containing', 'value': "Ничья", 'format': draw})
        worksheet.conditional_format('G2:G1000', {
                                     'type': 'text', 'criteria': 'containing', 'value': "Поражение", 'format': loss})
        worksheet.conditional_format('O2:O1000', {
                                     'type': 'text', 'criteria': 'containing', 'value': "дом", 'format': home})
        worksheet.conditional_format('O2:O1000', {
                                     'type': 'text', 'criteria': 'containing', 'value': "выезд", 'format': guest})
        worksheet.conditional_format('J2:J1000', {'type': '3_color_scale'})
        worksheet.conditional_format('K2:K1000', {'type': '3_color_scale'})

if __name__ == '__main__':
    parse("https://www.myscore.ru")
    #write_to_excel('C:/python-app/leagues')
