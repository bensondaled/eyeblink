import smtplib, logging

def email_alert(detail='(something needs your attention)', subject='Puffs Experiment Alert'):
    from_addr = 'bensondaledexperiments@gmail.com'
    to_addr = 'bendeverett@gmail.com'

    message = "\r\n".join([
                    "From: {}".format(from_addr),
                    "To: {}".format(to_addr),
                    "Subject: {}".format(subject),
                    "",
                    "{}".format(detail)
    ])

    try:
        smtpserver = smtplib.SMTP("smtp.gmail.com", 587)
        smtpserver.ehlo()
        smtpserver.starttls()
        smtpserver.ehlo()
        smtpserver.login('bensondaledexperiments@gmail.com', 'experiment')
        smtpserver.sendmail(from_addr, to_addr, message)
        smtpserver.close()
    except:
        logging.error('Email failed to send.')
