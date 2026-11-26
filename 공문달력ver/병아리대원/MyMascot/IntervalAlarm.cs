using System;
using System.Linq;

namespace MyMascot;

public class IntervalAlarm
{
	public bool Enabled;

	public int IntervalMinutes = 60;

	public string Type = "일반";

	public string Message = "";

	public DateTime LastFired = DateTime.MinValue;

	public static IntervalAlarm Parse(string line)
	{
		string[] array = line.Split(new char[1] { '|' });
		if (array.Length < 3)
		{
			return null;
		}
		if (!int.TryParse(array[1].Trim(), out var result) || result <= 0)
		{
			return null;
		}
		string type = "일반";
		int count = 2;
		if (array.Length >= 4 && Array.IndexOf(AlarmItem.Types, array[2].Trim()) >= 0)
		{
			type = array[2].Trim();
			count = 3;
		}
		IntervalAlarm intervalAlarm = new IntervalAlarm();
		intervalAlarm.Enabled = array[0].Trim() == "1";
		intervalAlarm.IntervalMinutes = result;
		intervalAlarm.Type = type;
		intervalAlarm.Message = string.Join("|", array.Skip(count));
		return intervalAlarm;
	}

	public string Serialize()
	{
		return (Enabled ? "1" : "0") + "|" + IntervalMinutes + "|" + Type + "|" + Message;
	}
}
