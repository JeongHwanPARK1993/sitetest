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
