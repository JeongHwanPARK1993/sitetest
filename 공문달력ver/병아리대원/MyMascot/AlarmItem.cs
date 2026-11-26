using System;
using System.Linq;

namespace MyMascot;

public class AlarmItem
{
	public static readonly string[] Types = new string[3] { "일반", "식사시간", "퇴근시간" };

	public bool Enabled;

	public string Time;

	public string Type = "일반";

	public string Message;

	public string LastFiredDate = "";

	public static AlarmItem Parse(string line)
	{
		string[] array = line.Split(new char[1] { '|' });
		if (array.Length < 3)
		{
			return null;
		}
		string type = "일반";
		int count = 2;
		if (array.Length >= 4 && Array.IndexOf(Types, array[2].Trim()) >= 0)
		{
			type = array[2].Trim();
			count = 3;
		}
		AlarmItem alarmItem = new AlarmItem();
		alarmItem.Enabled = array[0].Trim() == "1";
		alarmItem.Time = array[1].Trim();
		alarmItem.Type = type;
		alarmItem.Message = string.Join("|", array.Skip(count));
		return alarmItem;
	}

	public string Serialize()
	{
		return (Enabled ? "1" : "0") + "|" + Time + "|" + Type + "|" + Message;
	}
}
