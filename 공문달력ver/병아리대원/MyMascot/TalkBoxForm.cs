using System;
using System.Drawing;
using System.Windows.Forms;

namespace MyMascot;

/// <summary>
/// 병아리를 한 번 누르면 뜨는 '무슨 할 말 있어요?' 창.
/// 적은 말은 업무보조 달력이 공문 분석 방식으로 날짜·시간을 찾아 달력에 올린다. ("금요일 3시 회의")
/// </summary>
public class TalkBoxForm : Form
{
	private static readonly Color Cream = Color.FromArgb(255, 249, 236);

	private static readonly Color Brown = Color.FromArgb(120, 72, 20);

	private readonly TextBox input;

	private readonly Action<string> onMemo;

	private readonly Action onToday;

	public TalkBoxForm(Action<string> onMemo, Action onToday)
	{
		this.onMemo = onMemo;
		this.onToday = onToday;
		StartPosition = FormStartPosition.Manual;
		FormBorderStyle = FormBorderStyle.FixedToolWindow;
		Text = "병아리대원";
		ShowInTaskbar = false;
		TopMost = true;
		MaximizeBox = false;
		MinimizeBox = false;
		KeyPreview = true;
		BackColor = Cream;
		ClientSize = new Size(330, 150);
		Font = new Font("맑은 고딕", 9f);

		Label head = new Label();
		head.Text = "삐약! 무슨 할 말 있어요?";
		head.Font = new Font("맑은 고딕", 11f, FontStyle.Bold);
		head.ForeColor = Brown;
		head.Location = new Point(12, 10);
		head.AutoSize = true;
		Controls.Add(head);

		input = new TextBox();
		input.Location = new Point(12, 40);
		input.Width = 306;
		input.Font = new Font("맑은 고딕", 10.5f);
		Controls.Add(input);

		Label hint = new Label();
		hint.Text = "예) 금요일 3시 회의 · 내일까지 보고서 제출 · 12/3 교육";
		hint.ForeColor = Color.FromArgb(130, 120, 100);
		hint.Location = new Point(12, 72);
		hint.AutoSize = true;
		Controls.Add(hint);

		Button write = MakeButton("달력에 적기", 12, 104, 100);
		write.BackColor = Color.FromArgb(255, 214, 102);
		write.Click += delegate
		{
			Submit();
		};
		Button today = MakeButton("오늘 할 일 알려줘", 118, 104, 124);
		today.Click += delegate
		{
			Close();
			this.onToday();
		};
		Button close = MakeButton("닫기", 248, 104, 70);
		close.Click += delegate
		{
			Close();
		};
		AcceptButton = write;
		CancelButton = close;
		Shown += delegate
		{
			Activate();
			input.Focus();
		};
	}

	private Button MakeButton(string text, int x, int y, int w)
	{
		Button b = new Button();
		b.Text = text;
		b.Location = new Point(x, y);
		b.Size = new Size(w, 30);
		b.FlatStyle = FlatStyle.Flat;
		b.FlatAppearance.BorderColor = Color.FromArgb(220, 180, 110);
		b.BackColor = Color.White;
		b.ForeColor = Brown;
		Controls.Add(b);
		return b;
	}

	private void Submit()
	{
		string text = input.Text.Trim();
		if (text.Length == 0)
		{
			input.Focus();
			return;
		}
		Close();
		onMemo(text);
	}

	/// <summary>병아리 옆(위쪽)에 화면 밖으로 나가지 않게 띄운다.</summary>
	public void ShowNear(Rectangle chick)
	{
		Rectangle wa = Screen.FromRectangle(chick).WorkingArea;
		int x = chick.Left + chick.Width / 2 - Width / 2;
		int y = chick.Top - Height - 6;
		if (y < wa.Top)
		{
			y = chick.Bottom + 6;
		}
		x = Math.Max(wa.Left, Math.Min(x, wa.Right - Width));
		y = Math.Max(wa.Top, Math.Min(y, wa.Bottom - Height));
		Location = new Point(x, y);
		Show();
	}
}
