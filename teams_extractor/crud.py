from sqlalchemy.orm import Session
import models

def get_raw_message(db: Session, message_id: int):
    return db.query(models.RawMessage).filter(models.RawMessage.id == message_id).first()

def get_unprocessed_messages(db: Session, limit: int = 100):
    return db.query(models.RawMessage).filter(models.RawMessage.processed_status == False).limit(limit).all()

def create_raw_message(db: Session, raw_text: str, sender: str, timestamp: str):
    db_message = models.RawMessage(raw_text=raw_text, sender=sender, timestamp=timestamp)
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def mark_message_processed(db: Session, message_id: int):
    message = get_raw_message(db, message_id)
    if message:
        message.processed_status = True
        db.commit()

def create_contact(db: Session, primary_name: str, company: str = None, title: str = None, location: str = None, notes: str = None):
    db_contact = models.Contact(primary_name=primary_name, company=company, title=title, location=location, notes=notes)
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

def add_email_to_contact(db: Session, contact_id: int, email: str):
    db_email = models.ContactEmail(contact_id=contact_id, email=email)
    db.add(db_email)
    db.commit()

def add_phone_to_contact(db: Session, contact_id: int, phone: str):
    db_phone = models.ContactPhone(contact_id=contact_id, phone=phone)
    db.add(db_phone)
    db.commit()

def add_link_to_contact(db: Session, contact_id: int, url: str, type: str):
    db_link = models.ContactLink(contact_id=contact_id, url=url, type=type)
    db.add(db_link)
    db.commit()

def link_message_to_contact(db: Session, contact_id: int, raw_message_id: int):
    db_link = models.ContactMessage(contact_id=contact_id, raw_message_id=raw_message_id)
    db.add(db_link)
    db.commit()

def get_contacts(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Contact).offset(skip).limit(limit).all()
