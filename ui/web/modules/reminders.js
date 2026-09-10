export function createReminderController({ apiFetch, speakText }) {
  async function checkDueReminders() {
    try {
      const res = await apiFetch("/reminders/due");
      const data = await res.json();
      for (const reminder of data.due || []) {
        await speakText(`Reminder: ${reminder.text}`);
      }
    } catch {
      // transient — the next poll will pick up anything still due
    }
  }

  return { checkDueReminders };
}
