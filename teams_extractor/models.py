from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base
import datetime

class RawMessage(Base):
    __tablename__ = "raw_messages"

    id = Column(Integer, primary_key=True, index=True)
    raw_text = Column(Text, nullable=False)
    sender = Column(String, index=True)
    timestamp = Column(String) # Stored as string from Teams UI, can be parsed later
    processed_status = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    primary_name = Column(String, index=True)
    company = Column(String, index=True)
    title = Column(String)
    location = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    emails = relationship("ContactEmail", back_populates="contact", cascade="all, delete-orphan")
    phones = relationship("ContactPhone", back_populates="contact", cascade="all, delete-orphan")
    links = relationship("ContactLink", back_populates="contact", cascade="all, delete-orphan")
    messages = relationship("ContactMessage", back_populates="contact", cascade="all, delete-orphan")

class ContactEmail(Base):
    __tablename__ = "contact_emails"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    email = Column(String, index=True)

    contact = relationship("Contact", back_populates="emails")

class ContactPhone(Base):
    __tablename__ = "contact_phones"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    phone = Column(String, index=True)

    contact = relationship("Contact", back_populates="phones")

class ContactLink(Base):
    __tablename__ = "contact_links"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    url = Column(String)
    type = Column(String) # e.g., 'LinkedIn', 'Website'

    contact = relationship("Contact", back_populates="links")

class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    raw_message_id = Column(Integer, ForeignKey("raw_messages.id"))

    contact = relationship("Contact", back_populates="messages")
    raw_message = relationship("RawMessage")
