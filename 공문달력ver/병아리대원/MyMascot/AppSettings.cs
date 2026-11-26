using System;
using System.IO;
using System.Text;

namespace MyMascot;

public static class AppSettings
{
	public static string FilePath = AppPaths.Config("settings.txt");

	public static string GlowTheme = "노을";

	public static string LastGiftDate = "";

	public static void Load()
	{
		if (!File.Exists(FilePath))
		{
			Save();
			return;
		}
		string[] array = File.ReadAllLines(FilePath, Encoding.UTF8);
		foreach (string text in array)
		{
			string[] array2 = text.Split(new char[1] { '=' });
			if (array2.Length == 2 && array2[0].Trim() == "GlowTheme")
			{
				string text2 = array2[1].Trim();
				if (Array.IndexOf(EdgeGlowForm.ThemeNames, text2) >= 0)
				{
					GlowTheme = text2;
				}
			}
			if (array2.Length == 2 && array2[0].Trim() == "LastGiftDate")
			{
				LastGiftDate = array2[1].Trim();
			}
		}
	}

	public static void Save()
	{
		File.WriteAllLines(FilePath, new string[2]
		{
			"GlowTheme=" + GlowTheme,
			"LastGiftDate=" + LastGiftDate
		}, Encoding.UTF8);
	}
}
