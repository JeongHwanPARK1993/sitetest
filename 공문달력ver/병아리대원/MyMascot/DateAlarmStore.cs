using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

namespace MyMascot;

public static class DateAlarmStore
{
	public static string FilePath = AppPaths.Config("date_alarms.txt");

	public static List<DateAlarm> Load()
	{
		List<DateAlarm> list = new List<DateAlarm>();
		if (!File.Exists(FilePath))
		{
			return list;
		}
		string[] array = File.ReadAllLines(FilePath, Encoding.UTF8);
		foreach (string text in array)
		{
			if (!string.IsNullOrWhiteSpace(text) && !text.TrimStart(new char[0]).StartsWith(";"))
			{
				DateAlarm dateAlarm = DateAlarm.Parse(text);
				if (dateAlarm != null)
				{
					list.Add(dateAlarm);
				}
			}
		}
		return list;
	}

	public static void Save(List<DateAlarm> items)
	{
		string[] contents = items.Select((DateAlarm i) => i.Serialize()).ToArray();
		File.WriteAllLines(FilePath, contents, Encoding.UTF8);
	}
}
