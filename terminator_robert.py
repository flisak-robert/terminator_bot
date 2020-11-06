#!/usr/bin/python3

from telegram.ext import Updater, InlineQueryHandler, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler
from telegram import ReplyKeyboardRemove,ReplyKeyboardMarkup,InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton
import requests
import re
from bs4 import BeautifulSoup
import sys
from binascii import a2b_base64
#pip3 install git+https://github.com/codevance/python-deathbycaptcha.git
import deathbycaptcha

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintoshf  Mac OS X 10_12_6) AppeWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.78 Safari/537.36',
    'Connection': 'keep-alive'
}

#Create an empty list to store all available dates 
all_available_dates=[]

#Credentials for DeathByCaptcha
deathbycaptcha_username = 'DEATHBYCAPTCHA USER NAME HERE'
deathbycaptcha_password = 'DEATHBYCAPTCHA PASSWORD HERE'

#The bot is using callbacks from the user to perform some actions. It works with inline keyboard buttons.
# To successfully capture state and handle callback data, the variables are declared here.
#Stages
FIRST, SECOND = range(2)
#Callback data
ONE, TWO, THREE, FOUR = range(4)

#Create a session on the anmeldung website
session = requests.Session()
url = 'https://service.berlin.de/dienstleistung/120686/'
data = session.get(url, headers=headers)
soup = BeautifulSoup(data.text, 'html.parser')


#Start function defines bot behaviour when user types the /start command, 2 button menu is generated and callback data is collected for each click
def start(update, context):
    keyboard = [
        [
            InlineKeyboardButton('Anmelden', callback_data=str(ONE)),
            InlineKeyboardButton('Show a dog', callback_data=str(TWO))
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Hi ' + update.message.from_user.first_name + '! Please choose an option:' , reply_markup=reply_markup)
    return FIRST

#Define anmelden function that takes care of navigating to the page with calendars and finding available appointments
def anmelden(update, context):
    global all_available_dates
    global session
    global soup
    update.callback_query.edit_message_text(text="Searching for available appointments...")
    
    #Look for "Termin berlinweit suchen" button (url)
    products = soup.findAll('div', {'class': 'zmstermin-multi inner'})
    for p in products:
        link = p.find('a')['href']
        r = session.get(link)
    parseData = BeautifulSoup(r.text, 'html.parser')
    
    #check if there are available dates
    findDates = parseData.findAll('td', {'class': 'buchbar'})
    if len(findDates) == 0:
        sorryMsg = 'Sorry, but there are no available dates.\n It is also happens sometimes when something wrong with web page'
        update.callback_query.message.reply_text(sorryMsg)
        return SECOND
    
    else:
        #Declare a counter to distinguish between two visible calendar months and two lists to store months names and appointment urls
        counter = 0
        months = []
        appointment_urls = []
        
        #Find the two months names and store it in a list
        for m in parseData.findAll('th', {'class': 'month'}):
            month = m.text.strip()
            months.append(month)
        
        #Since there are two calendars, we need to store them both in the list
        soup = BeautifulSoup(r.content, "html.parser")
        appointment_list = soup.find_all('div', {'class': 'calendar-month-table span6'})

        #For each calendar, get the available appointment urls, the end goal is to create a key/value pair with appointment date and corresponding URL
        for buchbar in appointment_list:
            all_available = buchbar.find_all('td', {'class': 'buchbar'})
            for buchbar in all_available:
                appointment_url =  buchbar.find_all('a', href=True)
                for j in appointment_url:
                    appointment_urls.append(j['href'])
                    all_available_dates.append((buchbar.text.strip() + ' ' + months[counter], j['href']))
            counter = counter + 1
        
        #Create a dynamic menu with buttons for each appointment date and return FIRST as state
        query = update.callback_query
        query.answer()
        keyboard=[]
        keyboard.append([])
        for date,endpoint in all_available_dates:
            keyboard[0].append(InlineKeyboardButton(date, callback_data=date))
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text="Choose your appointment date", reply_markup=reply_markup)
        #Debug msg
        print(all_available_dates)
        print(len(all_available_dates))
        return FIRST

def appointment_choice(update, context):
    global session
    query = update.callback_query
    query.answer()
    #Debug message to see if the button is working
    query.message.reply_text('yaaay you have found an appointment date')
    query.edit_message_text(text='Selected option: {}'.format(query.data))
    
    #Create an URL based on the endpoint stored in the all_available_dates list
    for date,endpoint in all_available_dates:
        if query.data == date:
            url_date = 'https://service.berlin.de' + endpoint
    
    #debug message to see if the url is correct, create a session using this url
    print(url_date)
    r = session.get(url_date)
    
    #See where the bot is, probably stuck on captcha
    captcha_detected = r.url
    print(captcha_detected)
    parseData = BeautifulSoup(r.text, 'html.parser')
    if captcha_detected == 'https://service.berlin.de/terminvereinbarung/termin/human/':
        print('Captcha verification... please wait')
        captcha_container = parseData.find('form', {'action': '/terminvereinbarung/termin/human/'})
        captcha_image = captcha_container.find('img')
        captcha_image_url = captcha_image['src']
        #The URL looks like this: 'data:image/png;base64,iVBORw0KG...', base64 string is needed to generate the captcha image
        #Using string.partition() you put the string as function argument and then use the index [2] to get the remainder of the string
        #This array has 3 indexes (0,1,2):
        #0 - string that comes before the string from the input (in this case - its an empty string because data:image/png;base64 is the beginning of the string)
        #1 - is the string from the input
        #2 - what comes after the string from the input
        base64_from_url = captcha_image_url.partition("data:image/png;base64,")[2]
        
        #Generate a dynamic filename using base64 characters. First, get 10 characters, and then remove all the special characters,
        #since base64 can contain slashes and plus signs whcih could potentially be problematic as a filename
        base64_first_ten_chars = base64_from_url[0:10]
        captcha_filename = ''.join(e for e in base64_first_ten_chars if e.isalnum()) + '.png'

        #Save the image
        binary_data = a2b_base64(base64_from_url)
        fd = open(captcha_filename, 'wb')
        fd.write(binary_data)
        fd.close()

        #Send the image to DeathByCaptcha
        deathbycaptcha_timeout = 30 #30 second timeout for captcha solving, can be adjusted if it is too short
        deathbycaptcha_client = deathbycaptcha.SocketClient(deathbycaptcha_username, deathbycaptcha_password)
        try:
            captcha_to_resolve = deathbycaptcha_client.decode(captcha_filename, deathbycaptcha_timeout)
            if captcha_to_resolve:
                print("CAPTCHA %s solved: %s" % (captcha_to_resolve["captcha"], captcha_to_resolve["text"]))
                resolved_captcha = captcha_to_resolve["text"]
        except deathbycaptcha.AccessDeniedException:
            print('DeathByCaptcha Access DENIED')

        #The captcha form is a GET form so we need to modify the URL here with the right text
        #Example:
        #https://service.berlin.de/terminvereinbarung/termin/human/?captcha_text=hMddiv       
        captcha_getform_url = captcha_detected + '?captcha_text=' + resolved_captcha
        print(captcha_getform_url)
        r = session.get(captcha_getform_url)
        #Debug msg: CHECK CURRENT URL
        print(r.url)
        #For some reason it is redirecting to https://service.berlin.de/terminvereinbarung/termin/time/ and I believe this is
        #not the correct url and the date of the appointment scrapped from this URL is a default date (year 1970)
        #We need to recreate the session with the URL with endpoint, the one just before captcha redirect (variable: url_date)
        
        #Debug: See if the date is correct
        r = session.get(url_date)
        parseData = BeautifulSoup(r.text, 'html.parser')
        print(r.url)
        date_check = parseData.findAll('div', {'class': 'table-cell collapsible-description span7'})
        print(date_check)
        #The date is correct here so we are on the right page

        ##TO DO:
        # --- Get the hours of the appointment along with the burgeramt locations and display the buttons to the user
        # --- Create good callbacks to handle everything correctly in the next function

    else:
    #Code below is meant to find the exact hour of the appointments along with the burgeramt location however it won't work for now because captcha...
        print('NO captcha verification, yaaay!')
        parseData = BeautifulSoup(r.text, 'html.parser')
        available_hours = parseData.findAll('th', {'class': 'buchbar'})
        available_locations = parseData.findAll('td', {'class': 'frei'})
        is_error = parseData.findAll('div', {'class': 'alert alert-error noprint textile'})
        errors=[]
        for element in is_error:
            error_msg = element.text.strip()
            errors.append(error_msg)
        print(errors)
        hours = []
        locations = []
        for h in available_hours:
            hour = h.text.strip()
            hours.append(hour)
        print(hours)
        for l in available_locations:
            location = l.text.strip()
            locations.append(location)
        print(locations)
        return FIRST


#Needed to allow the bot to work when user types in the /start function without sending any callback data (so, without clicking a button)
#This is taken straight from the example on telegram bot GitHub
def start_over(update, context):
    """Prompt same text & keyboard as `start` does but not as new message"""
    # Get CallbackQuery from Update
    query = update.callback_query
    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()
    keyboard = [
        [
            InlineKeyboardButton('Anmelden', callback_data=str(ONE)),
            InlineKeyboardButton('Show a dog', callback_data=str(TWO))
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Instead of sending a new message, edit the message that
    # originated the CallbackQuery. This gives the feeling of an
    # interactive menu.
    query.edit_message_text(text='Hi try again' , reply_markup=reply_markup)
    return FIRST

#Dummy function to see if first menu is working correctly
def dog_choice(update, context):
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="You chose the second option")
    return FIRST

#End (under construction)
def end(update, context):
    """Returns `ConversationHandler.END`, which tells the
    ConversationHandler that the conversation is over"""
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="See you next time!")
    return ConversationHandler.END

# def list_all():
#     for i in all_available_dates:
#         print(i)

def main():
    updater = Updater('TOKEN HERE', use_context=True)
    dp = updater.dispatcher
    
    #Use ConversationHandler to handle conversation state based on the callback data received
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FIRST: [
                CallbackQueryHandler(anmelden, pattern='^' + str(ONE) + '$'),
                CallbackQueryHandler(dog_choice, pattern='^' + str(TWO) + '$'),
                
                #Callback data above is pretty straight forward, in this case, the callback data looks like this (example):
                #30 November 2020
                #As far as I know, this regex works in this case.
                CallbackQueryHandler(appointment_choice, pattern='^[0-9]* +[A-Za-z]')
            ],
            SECOND: [
                CallbackQueryHandler(start_over, pattern='^' + str(ONE) + '$'),
                CallbackQueryHandler(end, pattern='^' + str(TWO) + '$')
            ]
        },
        fallbacks=[CommandHandler('start', start)]
    )
    dp.add_handler(conv_handler)

    #dp.add_handler(MessageHandler(Filters.regex('^list$'), list_all()))
    updater.start_polling()

if __name__ == '__main__':
    main()
