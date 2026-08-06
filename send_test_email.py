import win32com.client
import sys

def send_test_email():
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        ns = outlook.GetNamespace("MAPI")
        current_user_email = ns.CurrentUser.AddressEntry.GetExchangeUser().PrimarySmtpAddress
        
        print(f"Detected local Outlook account: {current_user_email}")
        
        msg = outlook.CreateItem(0) # 0 = MailItem
        msg.To = current_user_email
        msg.Subject = "TalentOps AI - Local Verification Email"
        msg.Body = "Hello!\n\nThis is a verification email from TalentOps AI to confirm that local email sending is working properly.\n\nBest,\nAntigravity"
        
        msg.Send()
        print("Test email sent successfully!")
        
    except Exception as e:
        # Fallback if GetExchangeUser fails
        try:
            current_user_email = ns.CurrentUser.Address
            print(f"Fallback detected email: {current_user_email}")
            msg = outlook.CreateItem(0)
            msg.To = current_user_email
            msg.Subject = "TalentOps AI - Local Verification Email"
            msg.Body = "Hello!\n\nThis is a verification email from TalentOps AI to confirm that local email sending is working properly.\n\nBest,\nAntigravity"
            msg.Send()
            print("Test email sent successfully!")
        except Exception as fallback_e:
            print(f"Failed to send email: {e} | {fallback_e}")
            sys.exit(1)

if __name__ == "__main__":
    send_test_email()
