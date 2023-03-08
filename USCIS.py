import json
import csv
import requests
from lxml import html
import re
from time import sleep
from datetime import datetime

import smtplib

import pytextnow
# import multiprocessing as mp

carriers = {
	'att':    '@mms.att.net',
	'tmobile':' @tmomail.net',
	'verizon':  '@vtext.com',
	'sprint':   '@page.nextel.com'
}

def sendEmail(number, message, carrier):
	# for using gmail to send email, I found out we need to enable less secure apps - NOT RECOMMENDED: https://myaccount.google.com/lesssecureapps
	# Replace the number with your own, or consider using an argument\dict for multiple people.
	to_number = number + carriers[carrier]
	auth = ('email_id@gmail.com', 'password')

	# Establish a secure session with gmail's outgoing SMTP server using your gmail account
	server = smtplib.SMTP( "smtp.gmail.com", 587 )
	server.ehlo()
	server.starttls()
	server.ehlo()
	server.login(auth[0], auth[1])

	# Send text message through SMS gateway of destination number
	server.sendmail( auth[0], to_number, message)
	server.quit()

def sendSMS(number, message):
	sid = '' #obtain sid from TextNow - log in to the web UI, open developer options & find the SID in the cookies
	username = 'xxxxx'
	client = pytextnow.Client(username, cookie=sid)
	client.send_sms(number, message)

def GetCaseStatus(ReceiptNo):
	CaseStatus = dict()
	CaseStatus['ReceiptNo'] = ReceiptNo
	url = 'https://egov.uscis.gov/casestatus/mycasestatus.do'
	payload = {'completedActionsCurrentPage': '0', 'upcomingActionsCurrentPage': '0', 'appReceiptNum': ReceiptNo}
	r = requests.post(url, data=payload, verify=False)
	if r.status_code == 200:
		try:
			tree = html.fromstring(r.content)
			CaseStatus['status'] = tree.xpath('//h1')[0].text_content()
			CaseStatus['Message'] = tree.xpath('//div[@class="rows text-center"]/p')[0].text_content()
			if CaseStatus['Message']:
				try:
					CaseStatus['ReceiptDate'] = re.search('.*(On|As of) ([A-Za-z]* \d+, \d+), ', CaseStatus['Message']).group(2)
				except:
					CaseStatus['ReceiptDate'] = 'Not found'
				try:
					CaseStatus['ReceiptType'] = re.search('.*(Form ([^, ]*),|new card) .*', CaseStatus['Message']).group(1)
				except:
					CaseStatus['ReceiptType'] = 'Not found'
			else:
				CaseStatus['ReceiptDate'] = 'Not found'
				CaseStatus['ReceiptType'] = 'Not found'
		except IndexError:
			CaseStatus['status'] = 'Error'
			CaseStatus['Message'] = str(r.status_code) + ': Parse Error, website down?'
			CaseStatus['ReceiptDate'] = 'Error'
			CaseStatus['ReceiptType'] = 'Error'
	else:
		CaseStatus['status'] = 'Error'
		CaseStatus['Message'] = str(r.status_code)
		CaseStatus['ReceiptDate'] = 'Error'
		CaseStatus['ReceiptType'] = 'Error'
	return CaseStatus
		
if __name__ == '__main__':
	tryCount = 0
	maxTries = 5
	while tryCount < maxTries:
		try:
			lastStatus = ''
			lastCaseStatus = dict()
			run = 1
			while True:
				dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
				ReceiptNo = '######'
				CaseStatus = GetCaseStatus(ReceiptNo)
				statusText = CaseStatus['ReceiptNo'] + ", " + CaseStatus['ReceiptDate'] + ", " + CaseStatus['ReceiptType'] + ", " + CaseStatus['status']
				print(dt_string + ": " + statusText)
				# sendEmail('###', statusText, 'tmobile')
				#if statusText != lastStatus:
				if lastCaseStatus != CaseStatus:
					if run > 1:
						sendSMS('###', statusText)
					lastStatus = statusText
					lastCaseStatus = CaseStatus
				run = run + 1
				sleep(300)
		except Exception as e:
			tryCount = tryCount + 1
			print(e)
			sleep(300)
	else:
		try:
			sendSMS('###', 'USCIS status check script error occured. Script stopped.')
		except Exception as ex:
			sendEmail('###', 'USCIS Script error and SMS failed.', 'tmobile')
		
