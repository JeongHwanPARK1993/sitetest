using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;

namespace MyMascot;

public class TrayAppContext : ApplicationContext
{
	private NotifyIcon trayIcon;

	private MascotForm mascot;

	private List<AlarmItem> alarms;

	private List<IntervalAlarm> intervalAlarms;

	private List<DateAlarm> dateAlarms;

	private Timer alarmTimer;

	public TrayAppContext()
	{
		//IL_00ef: Unknown result type (might be due to invalid IL or missing references)
		//IL_00f5: Expected O, but got Unknown
		//IL_00a2: Unknown result type (might be due to invalid IL or missing references)
		//IL_00ac: Expected O, but got Unknown
		//IL_0147: Unknown result type (might be due to invalid IL or missing references)
		//IL_0151: Expected O, but got Unknown
		//IL_0163: Unknown result type (might be due to invalid IL or missing references)
		//IL_016d: Expected O, but got Unknown
		//IL_020e: Unknown result type (might be due to invalid IL or missing references)
		//IL_0218: Expected O, but got Unknown
		//IL_0277: Unknown result type (might be due to invalid IL or missing references)
		//IL_0281: Expected O, but got Unknown
		AppSettings.Load();
		AutoStart.RefreshPathIfEnabled();
		alarms = AlarmStore.Load();
		intervalAlarms = IntervalAlarmStore.Load();
		dateAlarms = DateAlarmStore.Load();
		foreach (IntervalAlarm intervalAlarm in intervalAlarms)
		{
			intervalAlarm.LastFired = DateTime.Now;
		}
		mascot = new MascotForm();
		((Control)mascot).Show();
		trayIcon = new NotifyIcon();
		Icon val = null;
		try
		{
			val = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
		}
		catch
		{
		}
		trayIcon.Icon = val ?? SystemIcons.Application;
		trayIcon.Visible = true;
		trayIcon.Text = "병아리대원";
		ContextMenuStrip val2 = new ContextMenuStrip();
		((ToolStrip)val2).Items.Add("알람 설정", (Image)null, (EventHandler)delegate
		{
			OpenSettings();
		});
		((ToolStrip)val2).Items.Add("캐릭터 보이기/숨기기", (Image)null, (EventHandler)delegate
		{
			((Control)mascot).Visible = !((Control)mascot).Visible;
		});
		ToolStripMenuItem quietItem = new ToolStripMenuItem("얌전모드");
		quietItem.CheckOnClick = true;
		ToolStripMenuItem focusItem = new ToolStripMenuItem("집중모드");
		focusItem.CheckOnClick = true;
		((ToolStripItem)quietItem).Click += delegate
		{
			mascot.SetQuietMode(quietItem.Checked);
			if (quietItem.Checked)
			{
				focusItem.Checked = false;
			}
		};
		((ToolStripItem)focusItem).Click += delegate
		{
			mascot.SetFocusMode(focusItem.Checked);
			if (focusItem.Checked)
			{
				quietItem.Checked = false;
			}
		};
		mascot.FocusModeChanged += delegate(bool on)
		{
			focusItem.Checked = on;
		};
		((ToolStrip)val2).Items.Add((ToolStripItem)(object)focusItem);
		((ToolStrip)val2).Items.Add((ToolStripItem)(object)quietItem);
		((ToolStrip)val2).Items.Add("대화", (Image)null, (EventHandler)delegate
		{
			mascot.TriggerContextualSpeech();
		});
		((ToolStrip)val2).Items.Add((ToolStripItem)new ToolStripSeparator());
		((ToolStrip)val2).Items.Add("종료", (Image)null, (EventHandler)delegate
		{
			ExitApp();
		});
		trayIcon.ContextMenuStrip = val2;
		trayIcon.DoubleClick += delegate
		{
			OpenSettings();
		};
		((Control)mascot).ContextMenuStrip = val2;
		alarmTimer = new Timer();
		alarmTimer.Interval = 5000;
		alarmTimer.Tick += delegate
		{
			CheckAlarms();
			CalendarBridge.Poll(mascot);
		};
		alarmTimer.Start();
	}

	private void CheckAlarms()
	{
		string text = DateTime.Now.ToString("yyyy-MM-dd HH:mm");
		string text2 = DateTime.Now.ToString("HH:mm");
		foreach (AlarmItem alarm in alarms)
		{
			if (alarm.Enabled && alarm.Time == text2 && alarm.LastFiredDate != text)
			{
				alarm.LastFiredDate = text;
				mascot.ShowAlert(alarm.Message, alarm.Type);
			}
		}
		foreach (IntervalAlarm intervalAlarm in intervalAlarms)
		{
			if (intervalAlarm.Enabled && (DateTime.Now - intervalAlarm.LastFired).TotalMinutes >= (double)intervalAlarm.IntervalMinutes)
			{
				intervalAlarm.LastFired = DateTime.Now;
				mascot.ShowAlert(intervalAlarm.Message, intervalAlarm.Type);
			}
		}
		string text3 = DateTime.Now.ToString("yyyy-MM-dd");
		foreach (DateAlarm dateAlarm in dateAlarms)
		{
			if (dateAlarm.Enabled && dateAlarm.Date == text3 && dateAlarm.Time == text2 && dateAlarm.LastFiredKey != text)
			{
				dateAlarm.LastFiredKey = text;
				mascot.ShowAlert(dateAlarm.Memo, "일반");
			}
		}
	}

	private void OpenSettings()
	{
		//IL_0019: Unknown result type (might be due to invalid IL or missing references)
		//IL_001f: Invalid comparison between Unknown and I4
		SettingsForm settingsForm = new SettingsForm(alarms, intervalAlarms, dateAlarms);
		try
		{
			if ((int)((Form)settingsForm).ShowDialog() != 1)
			{
				return;
			}
			alarms = settingsForm.Result;
			AlarmStore.Save(alarms);
			dateAlarms = settingsForm.DateResult;
			DateAlarmStore.Save(dateAlarms);
			List<IntervalAlarm> intervalResult = settingsForm.IntervalResult;
			foreach (IntervalAlarm ia in intervalResult)
			{
				List<IntervalAlarm> source = intervalAlarms;
				Func<IntervalAlarm, bool> predicate = (IntervalAlarm p) => p.IntervalMinutes == ia.IntervalMinutes && p.Message == ia.Message;
				IntervalAlarm intervalAlarm = source.FirstOrDefault(predicate);
				ia.LastFired = intervalAlarm?.LastFired ?? DateTime.Now;
			}
			intervalAlarms = intervalResult;
			IntervalAlarmStore.Save(intervalAlarms);
		}
		finally
		{
			((IDisposable)settingsForm)?.Dispose();
		}
	}

	private void ExitApp()
	{
		trayIcon.Visible = false;
		((Form)mascot).Close();
		Application.Exit();
	}
}
