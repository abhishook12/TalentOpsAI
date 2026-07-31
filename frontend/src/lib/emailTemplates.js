// src/lib/emailTemplates.js
const TEMPLATES_KEY = 'talentops_saved_templates';
const LAST_EMAIL_KEY = 'talentops_last_email_memory';

export const getSavedTemplates = () => {
  try {
    const data = localStorage.getItem(TEMPLATES_KEY);
    return data ? JSON.parse(data) : [];
  } catch (e) {
    console.error('Failed to load templates:', e);
    return [];
  }
};

export const saveTemplate = (template) => {
  try {
    const templates = getSavedTemplates();
    const newTemplate = {
      ...template,
      id: Date.now().toString(),
      createdAt: new Date().toISOString()
    };
    templates.unshift(newTemplate);
    localStorage.setItem(TEMPLATES_KEY, JSON.stringify(templates));
    return newTemplate;
  } catch (e) {
    console.error('Failed to save template:', e);
    return null;
  }
};

export const deleteTemplate = (id) => {
  try {
    const templates = getSavedTemplates();
    const updated = templates.filter(t => t.id !== id);
    localStorage.setItem(TEMPLATES_KEY, JSON.stringify(updated));
    return true;
  } catch (e) {
    console.error('Failed to delete template:', e);
    return false;
  }
};

export const getLastEmail = () => {
  try {
    const data = localStorage.getItem(LAST_EMAIL_KEY);
    return data ? JSON.parse(data) : null;
  } catch (e) {
    return null;
  }
};

export const setLastEmail = (subject, body) => {
  try {
    const payload = {
      subject,
      body,
      updatedAt: new Date().toISOString()
    };
    localStorage.setItem(LAST_EMAIL_KEY, JSON.stringify(payload));
  } catch (e) {
    console.error('Failed to save last email:', e);
  }
};
