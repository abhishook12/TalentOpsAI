import asyncio
from aiosmtpd.controller import Controller

class CustomHandler:
    async def handle_DATA(self, server, session, envelope):
        print("\n" + "="*60)
        print("MOCK SMTP SERVER RECEIVED EMAIL!")
        print("="*60)
        print(f"From: {envelope.mail_from}")
        print(f"To: {envelope.rcpt_tos}")
        print("Message Data:")
        print(envelope.content.decode('utf8', errors='replace'))
        print("="*60 + "\n")
        return '250 Message accepted for delivery'

if __name__ == '__main__':
    controller = Controller(CustomHandler(), hostname='127.0.0.1', port=1025)
    controller.start()
    print("Mock SMTP Server listening on 127.0.0.1:1025")
    
    # Run forever
    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        pass
