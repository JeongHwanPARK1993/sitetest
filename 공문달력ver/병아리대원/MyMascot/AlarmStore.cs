using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

namespace MyMascot;

public static class AlarmStore
{
	public static string FilePath = AppPaths.Config("alarms.txt");

	public static List<AlarmItem> Load()
	{
		List<AlarmItem> list = new List<AlarmItem>();
		if (!File.Exists(FilePath))
		{
			File.WriteAllLines(FilePath, new string[2] { "1|12:00|식사시간|점심 먹으러 가자!", "1|18:00|퇴근시간|퇴근이다! 오늘도 수고했어" }, Encoding.UTF8);
		}
		string[] array = File.ReadAllLines(FilePath, Encoding.UTF8);
		foreach (string text in array)
		{
			if (!string.IsNullOrWhiteSpace(text) && !text.TrimStart(new char[0]).StartsWith(";"))
			{
				AlarmItem alarmItem = AlarmItem.Parse(text);
				if (alarmItem != null)
				{
					list.Add(alarmItem);
				}
			}
		}
		return list;
	}

	public static void Save(List<AlarmItem> items)
	{
		string[] contents = items.Select((AlarmItem i) => i.Serialize()).ToArray();
		File.WriteAllLines(FilePath, contents, Encoding.UTF8);
	}
}
