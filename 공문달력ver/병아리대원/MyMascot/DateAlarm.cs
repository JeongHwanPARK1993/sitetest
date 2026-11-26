using System.Linq;

namespace MyMascot;

public class DateAlarm
{
	public bool Enabled;

	public string Date;

	public string Time;

	public string Memo = "";

	public string LastFiredKey = "";

	public static DateAlarm Parse(string line)
	{
		string[] array = line.Split(new char[1] { '|' });
		if (array.Length < 4)
		{
			return null;
		}
		DateAlarm dateAlarm = new DateAlarm();
		dateAlarm.Enabled = array[0].Trim() == "1";
		dateAlarm.Date = array[1].Trim();
		dateAlarm.Time = array[2].Trim();
		dateAlarm.Memo = string.Join("|", array.Skip(3));
		return dateAlarm;
	}

	public string Serialize()
	{
		return (Enabled ? "1" : "0") + "|" + Date + "|" + Time + "|" + Memo.Replace("\r", "").Replace("\n", " ");
	}
}
