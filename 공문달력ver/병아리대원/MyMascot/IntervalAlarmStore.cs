using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

namespace MyMascot;

public static class IntervalAlarmStore
{
	public static string FilePath = AppPaths.Config("interval_alarms.txt");

	public static List<IntervalAlarm> Load()
	{
		List<IntervalAlarm> list = new List<IntervalAlarm>();
		if (!File.Exists(FilePath))
		{
			File.WriteAllLines(FilePath, new string[1] { "0|60|일반|물 한 잔 마시고 스트레칭 한 번 해요" }, Encoding.UTF8);
		}
		string[] array = File.ReadAllLines(FilePath, Encoding.UTF8);
		foreach (string text in array)
		{
			if (!string.IsNullOrWhiteSpace(text) && !text.TrimStart(new char[0]).StartsWith(";"))
			{
				IntervalAlarm intervalAlarm = IntervalAlarm.Parse(text);
				if (intervalAlarm != null)
				{
					list.Add(intervalAlarm);
				}
			}
		}
		return list;
	}

	public static void Save(List<IntervalAlarm> items)
	{
		string[] contents = items.Select((IntervalAlarm i) => i.Serialize()).ToArray();
		File.WriteAllLines(FilePath, contents, Encoding.UTF8);
	}
}
