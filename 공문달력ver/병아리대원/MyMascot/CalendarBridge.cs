using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace MyMascot;

/// <summary>
/// 업무보조 달력과 병아리대원을 잇는 다리 (같은 PC 안의 파일로만 주고받는다. 인터넷 사용 없음)
///   %APPDATA%\병아리대원\달력연결\inbox.txt   : 달력 → 병아리   한 줄에 "번호 [탭] 할 말 [탭] 진행중일 때 다시 물을 시간(선택)"
///   %APPDATA%\병아리대원\달력연결\outbox.txt  : 병아리 → 달력   한 줄에 "번호 [탭] 대답(done/progress/mute/ignore)"
/// </summary>
public static class CalendarBridge
{
	private static readonly string[] Options = new string[3] { "완료", "진행중", "알람끄기" };

	private static readonly string[] Answers = new string[3] { "done", "progress", "mute" };

	private static readonly string[] ThanksLines = new string[4] { "잘했어요! 달력에 처리 완료로 적어 둘게요.", "역시 최고예요! 처리 완료!", "삐약! 하나 끝냈어요. 수고했어요!", "완료 표시 했어요. 다음 일도 같이 챙겨요!" };

	private static readonly HashSet<string> handled = new HashSet<string>();

	private static readonly UTF8Encoding Utf8 = new UTF8Encoding(false);

	private static readonly Random rnd = new Random();

	private static bool asking;

	public static string Dir => Path.Combine(AppPaths.DataDir, "달력연결");

	private static string Inbox => Path.Combine(Dir, "inbox.txt");

	private static string Outbox => Path.Combine(Dir, "outbox.txt");

	private static string SettingsFile => Path.Combine(Dir, "settings.txt");

	private static string UpcomingFile => Path.Combine(Dir, "upcoming.txt");

	/// <summary>달력이 연결된 적이 있는가 (달력이 설정 파일을 만들어 둔다)</summary>
	public static bool Linked => File.Exists(SettingsFile);

	/// <summary>달력 알람 설정 (key=value). 달력과 병아리대원이 같이 쓰고, 고친 쪽이 다른 쪽에 반영된다.</summary>
	public static Dictionary<string, string> ReadSettings()
	{
		Dictionary<string, string> d = new Dictionary<string, string>();
		try
		{
			if (File.Exists(SettingsFile))
			{
				foreach (string line in File.ReadAllLines(SettingsFile, Encoding.UTF8))
				{
					int eq = line.IndexOf('=');
					if (eq > 0)
					{
						d[line.Substring(0, eq).Trim()] = line.Substring(eq + 1).Trim();
					}
				}
			}
		}
		catch
		{
		}
		return d;
	}

	public static void WriteSettings(Dictionary<string, string> d)
	{
		try
		{
			Directory.CreateDirectory(Dir);
			List<string> lines = new List<string>();
			foreach (KeyValuePair<string, string> kv in d)
			{
				lines.Add(kv.Key + "=" + kv.Value);
			}
			string tmp = SettingsFile + ".tmp";
			File.WriteAllLines(tmp, lines.ToArray(), Utf8);
			if (File.Exists(SettingsFile))
			{
				File.Delete(SettingsFile);
			}
			File.Move(tmp, SettingsFile);
		}
		catch
		{
		}
	}

	/// <summary>달력이 적어 둔 '지금 챙길 일' 목록: 한 줄에 날짜 [탭] 제목 [탭] 상태</summary>
	public static List<string[]> ReadUpcoming()
	{
		List<string[]> list = new List<string[]>();
		try
		{
			if (File.Exists(UpcomingFile))
			{
				foreach (string line in File.ReadAllLines(UpcomingFile, Encoding.UTF8))
				{
					string[] p = line.Split('\t');
					if (p.Length >= 2)
					{
						list.Add(p);
					}
				}
			}
		}
		catch
		{
		}
		return list;
	}

	/// <summary>5초마다 불린다: 아직 묻지 않은 달력 질문이 있으면 하나 꺼내서 묻는다.</summary>
	public static void Poll(MascotForm mascot)
	{
		if (asking || !File.Exists(Inbox))
		{
			return;
		}
		string[] lines;
		try
		{
			lines = File.ReadAllLines(Inbox, Encoding.UTF8);
		}
		catch
		{
			return;
		}
		foreach (string line in lines)
		{
			int tab = line.IndexOf('\t');
			if (tab <= 0)
			{
				continue;
			}
			string key = line.Substring(0, tab).Trim();
			string[] rest = line.Substring(tab + 1).Split('\t');
			string message = rest[0].Trim();
			string later = (rest.Length > 1) ? rest[1].Trim() : "";
			if (key.Length == 0 || message.Length == 0 || handled.Contains(key))
			{
				continue;
			}
			handled.Add(key);
			Ask(mascot, key, message, later);
			break;
		}
	}

	private static void Ask(MascotForm mascot, string key, string message, string later)
	{
		asking = true;
		mascot.AskCalendar(message, Options, delegate(int pick)
		{
			asking = false;
			Reply(key, Answers[pick]);
			if (pick == 0)
			{
				mascot.SayCalendar(ThanksLines[rnd.Next(ThanksLines.Length)]);
			}
			else if (pick == 1)
			{
				mascot.SayCalendar(later.Length > 0 ? ("화이팅! " + later + " 뒤에 다시 물어볼게요.") : "화이팅! 나중에 다시 물어볼게요.");
			}
			else
			{
				mascot.SayCalendar("알겠어요. 이 일은 더 안 물어볼게요.");
			}
		}, delegate
		{
			asking = false;
			Reply(key, "ignore");
		});
	}

	private static void Reply(string key, string answer)
	{
		try
		{
			Directory.CreateDirectory(Dir);
			File.AppendAllText(Outbox, key + "\t" + answer + Environment.NewLine, Utf8);
		}
		catch
		{
		}
	}
}
