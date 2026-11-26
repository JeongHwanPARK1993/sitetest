using System;
using System.Collections;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;

namespace MyMascot;

public class SettingsForm : Form
{
	private DataGridView grid;

	private DataGridView intervalGrid;

	private DataGridView dateGrid;

	private Button btnAdd;

	private Button btnDelete;

	private Button btnSave;

	private Button btnCancel;

	private Button btnIntervalAdd;

	private Button btnIntervalDelete;

	private Button btnDateAdd;

	private Button btnDateDelete;

	private ComboBox themeCombo;

	private CheckBox autoStartCheck;

	private EdgeGlowForm previewGlow;

	private Timer previewGlowTimer;

	public List<AlarmItem> Result;

	public List<IntervalAlarm> IntervalResult;

	public List<DateAlarm> DateResult;

	private List<AlarmItem> working;

	private List<IntervalAlarm> intervalWorking;

	private static readonly Color TimeLight = Color.FromArgb(227, 240, 255);

	private static readonly Color TimeHeader = Color.FromArgb(150, 195, 245);

	private static readonly Color TimeSelect = Color.FromArgb(70, 130, 210);

	private static readonly Color IntervalLight = Color.FromArgb(228, 246, 228);

	private static readonly Color IntervalHeader = Color.FromArgb(150, 210, 150);

	private static readonly Color IntervalSelect = Color.FromArgb(60, 150, 80);

	private static readonly Color DateLight = Color.FromArgb(255, 238, 222);

	private static readonly Color DateHeader = Color.FromArgb(245, 180, 120);

	private static readonly Color DateSelect = Color.FromArgb(220, 120, 50);

	public SettingsForm(List<AlarmItem> current, List<IntervalAlarm> currentInterval, List<DateAlarm> currentDate)
	{
		//IL_00c9: Unknown result type (might be due to invalid IL or missing references)
		//IL_00d3: Expected O, but got Unknown
		//IL_0149: Unknown result type (might be due to invalid IL or missing references)
		//IL_0150: Expected O, but got Unknown
		//IL_017e: Unknown result type (might be due to invalid IL or missing references)
		//IL_0185: Expected O, but got Unknown
		//IL_01b3: Unknown result type (might be due to invalid IL or missing references)
		//IL_01ba: Expected O, but got Unknown
		//IL_0280: Unknown result type (might be due to invalid IL or missing references)
		//IL_028a: Expected O, but got Unknown
		//IL_028b: Unknown result type (might be due to invalid IL or missing references)
		//IL_0295: Expected O, but got Unknown
		//IL_02f0: Unknown result type (might be due to invalid IL or missing references)
		//IL_02f7: Expected O, but got Unknown
		//IL_032b: Unknown result type (might be due to invalid IL or missing references)
		//IL_0332: Expected O, but got Unknown
		//IL_0366: Unknown result type (might be due to invalid IL or missing references)
		//IL_036d: Expected O, but got Unknown
		//IL_03c5: Unknown result type (might be due to invalid IL or missing references)
		//IL_03cc: Expected O, but got Unknown
		//IL_04a1: Unknown result type (might be due to invalid IL or missing references)
		//IL_04a8: Expected O, but got Unknown
		//IL_0507: Unknown result type (might be due to invalid IL or missing references)
		//IL_050e: Expected O, but got Unknown
		//IL_0583: Unknown result type (might be due to invalid IL or missing references)
		//IL_058d: Expected O, but got Unknown
		//IL_05e8: Unknown result type (might be due to invalid IL or missing references)
		//IL_05ef: Expected O, but got Unknown
		//IL_0623: Unknown result type (might be due to invalid IL or missing references)
		//IL_062a: Expected O, but got Unknown
		//IL_065e: Unknown result type (might be due to invalid IL or missing references)
		//IL_0665: Expected O, but got Unknown
		//IL_0734: Unknown result type (might be due to invalid IL or missing references)
		//IL_073b: Expected O, but got Unknown
		//IL_079a: Unknown result type (might be due to invalid IL or missing references)
		//IL_07a1: Expected O, but got Unknown
		//IL_0801: Unknown result type (might be due to invalid IL or missing references)
		//IL_080b: Expected O, but got Unknown
		//IL_0866: Unknown result type (might be due to invalid IL or missing references)
		//IL_086d: Expected O, but got Unknown
		//IL_08a1: Unknown result type (might be due to invalid IL or missing references)
		//IL_08a8: Expected O, but got Unknown
		//IL_08dc: Unknown result type (might be due to invalid IL or missing references)
		//IL_08e3: Expected O, but got Unknown
		//IL_0917: Unknown result type (might be due to invalid IL or missing references)
		//IL_091e: Expected O, but got Unknown
		//IL_0991: Unknown result type (might be due to invalid IL or missing references)
		//IL_0998: Expected O, but got Unknown
		//IL_0a18: Unknown result type (might be due to invalid IL or missing references)
		//IL_0a1f: Expected O, but got Unknown
		//IL_0a7e: Unknown result type (might be due to invalid IL or missing references)
		//IL_0a85: Expected O, but got Unknown
		//IL_0afa: Unknown result type (might be due to invalid IL or missing references)
		//IL_0b01: Expected O, but got Unknown
		//IL_0b4c: Unknown result type (might be due to invalid IL or missing references)
		//IL_0b53: Expected O, but got Unknown
		//IL_0b8c: Unknown result type (might be due to invalid IL or missing references)
		//IL_0b93: Expected O, but got Unknown
		//IL_0c11: Unknown result type (might be due to invalid IL or missing references)
		//IL_0c18: Expected O, but got Unknown
		//IL_0c6f: Unknown result type (might be due to invalid IL or missing references)
		//IL_0c76: Expected O, but got Unknown
		//IL_0c8e: Unknown result type (might be due to invalid IL or missing references)
		//IL_0c98: Expected O, but got Unknown
		//IL_0cfd: Unknown result type (might be due to invalid IL or missing references)
		//IL_0d04: Expected O, but got Unknown
		//IL_0cee: Unknown result type (might be due to invalid IL or missing references)
		//IL_0cf5: Expected O, but got Unknown
		//IL_0d67: Unknown result type (might be due to invalid IL or missing references)
		//IL_0d6e: Expected O, but got Unknown
		DataGridViewCellFormattingEventHandler val = null;
		FormClosedEventHandler val2 = null;
		working = current.Select((AlarmItem a) => new AlarmItem
		{
			Enabled = a.Enabled,
			Time = a.Time,
			Type = a.Type,
			Message = a.Message
		}).ToList();
		intervalWorking = currentInterval.Select((IntervalAlarm a) => new IntervalAlarm
		{
			Enabled = a.Enabled,
			IntervalMinutes = a.IntervalMinutes,
			Type = a.Type,
			Message = a.Message
		}).ToList();
		((Control)this).Text = "병아리대원 알람 설정";
		((Control)this).Width = 560;
		((Control)this).Height = 460;
		((Form)this).StartPosition = (FormStartPosition)1;
		((Form)this).FormBorderStyle = (FormBorderStyle)3;
		((Form)this).MaximizeBox = false;
		((Form)this).MinimizeBox = false;
		TabControl tabs = new TabControl();
		((Control)tabs).Location = new Point(10, 10);
		((Control)tabs).Size = new Size(530, 335);
		tabs.DrawMode = (TabDrawMode)1;
		tabs.SizeMode = (TabSizeMode)2;
		tabs.ItemSize = new Size(110, 26);
		((Control)this).Controls.Add((Control)(object)tabs);
		TabPage val3 = new TabPage("시간 알람");
		((Control)val3).BackColor = TimeLight;
		val3.UseVisualStyleBackColor = false;
		TabPage val4 = val3;
		tabs.TabPages.Add(val4);
		TabPage val5 = new TabPage("반복 알람");
		((Control)val5).BackColor = IntervalLight;
		val5.UseVisualStyleBackColor = false;
		TabPage val6 = val5;
		tabs.TabPages.Add(val6);
		TabPage val7 = new TabPage("일정 알람");
		((Control)val7).BackColor = DateLight;
		val7.UseVisualStyleBackColor = false;
		TabPage val8 = val7;
		tabs.TabPages.Add(val8);
		TabPage calPage = new TabPage("달력 알람");
		((Control)calPage).BackColor = Color.FromArgb(255, 249, 236);
		calPage.UseVisualStyleBackColor = false;
		tabs.TabPages.Add(calPage);
		BuildCalendarTab(calPage);
		Color[] tabColors = new Color[4] { TimeHeader, IntervalHeader, DateHeader, Color.FromArgb(255, 204, 128) };
		Color[] tabSelColors = new Color[4] { TimeSelect, IntervalSelect, DateSelect, Color.FromArgb(232, 140, 30) };
		tabs.DrawItem += (DrawItemEventHandler)delegate(object s, DrawItemEventArgs e)
		{
			//IL_004c: Unknown result type (might be due to invalid IL or missing references)
			//IL_0052: Expected O, but got Unknown
			//IL_007c: Unknown result type (might be due to invalid IL or missing references)
			//IL_0082: Expected O, but got Unknown
			bool flag = e.Index == tabs.SelectedIndex;
			Rectangle bounds = e.Bounds;
			SolidBrush val37 = new SolidBrush(flag ? tabSelColors[e.Index] : tabColors[e.Index]);
			try
			{
				e.Graphics.FillRectangle((Brush)(object)val37, bounds);
			}
			finally
			{
				((IDisposable)val37)?.Dispose();
			}
			Font val38 = new Font("맑은 고딕", 9f, (FontStyle)(flag ? 1 : 0));
			try
			{
				TextRenderer.DrawText((IDeviceContext)(object)e.Graphics, ((Control)tabs.TabPages[e.Index]).Text, val38, bounds, flag ? Color.White : Color.FromArgb(40, 40, 40), (TextFormatFlags)5);
			}
			finally
			{
				((IDisposable)val38)?.Dispose();
			}
		};
		grid = new DataGridView();
		((Control)grid).Location = new Point(5, 5);
		((Control)grid).Size = new Size(510, 265);
		grid.AllowUserToAddRows = false;
		grid.AllowUserToDeleteRows = false;
		grid.RowHeadersVisible = false;
		DataGridViewColumnCollection columns = grid.Columns;
		DataGridViewCheckBoxColumn val9 = new DataGridViewCheckBoxColumn();
		((DataGridViewColumn)val9).Name = "Enabled";
		((DataGridViewColumn)val9).HeaderText = "사용";
		((DataGridViewColumn)val9).Width = 50;
		columns.Add((DataGridViewColumn)(object)val9);
		DataGridViewColumnCollection columns2 = grid.Columns;
		DataGridViewTextBoxColumn val10 = new DataGridViewTextBoxColumn();
		((DataGridViewColumn)val10).Name = "Time";
		((DataGridViewColumn)val10).HeaderText = "시간 (0900)";
		((DataGridViewColumn)val10).Width = 90;
		columns2.Add((DataGridViewColumn)(object)val10);
		AttachDateTimeInput(grid);
		DataGridViewComboBoxColumn val11 = new DataGridViewComboBoxColumn();
		((DataGridViewColumn)val11).Name = "Type";
		((DataGridViewColumn)val11).HeaderText = "유형";
		((DataGridViewColumn)val11).Width = 100;
		DataGridViewComboBoxColumn val12 = val11;
		val12.Items.AddRange((object[])AlarmItem.Types);
		val12.FlatStyle = (FlatStyle)0;
		grid.Columns.Add((DataGridViewColumn)(object)val12);
		DataGridViewColumnCollection columns3 = grid.Columns;
		DataGridViewTextBoxColumn val13 = new DataGridViewTextBoxColumn();
		((DataGridViewColumn)val13).Name = "Message";
		((DataGridViewColumn)val13).HeaderText = "문구";
		((DataGridViewColumn)val13).Width = 250;
		columns3.Add((DataGridViewColumn)(object)val13);
		((Control)val4).Controls.Add((Control)(object)grid);
		StyleGrid(grid, TimeLight, TimeHeader, TimeSelect);
		foreach (AlarmItem item in working)
		{
			grid.Rows.Add(new object[4] { item.Enabled, item.Time, item.Type, item.Message });
		}
		Button val14 = new Button();
		((Control)val14).Text = "알람 추가";
		((Control)val14).Location = new Point(5, 275);
		((Control)val14).Width = 100;
		btnAdd = val14;
		((Control)btnAdd).Click += delegate
		{
			grid.Rows.Add(new object[4] { true, "09:00", "일반", "새 알람" });
		};
		((Control)val4).Controls.Add((Control)(object)btnAdd);
		Button val15 = new Button();
		((Control)val15).Text = "선택 삭제";
		((Control)val15).Location = new Point(115, 275);
		((Control)val15).Width = 100;
		btnDelete = val15;
		((Control)btnDelete).Click += delegate
		{
			//IL_0019: Unknown result type (might be due to invalid IL or missing references)
			//IL_001f: Expected O, but got Unknown
			foreach (DataGridViewRow item2 in (BaseCollection)grid.SelectedRows)
			{
				DataGridViewRow val37 = item2;
				if (!val37.IsNewRow)
				{
					grid.Rows.Remove(val37);
				}
			}
		};
		((Control)val4).Controls.Add((Control)(object)btnDelete);
		((Control)val4).Controls.Add((Control)(object)HintLabel("※ 시간은 숫자 4자리로 입력해요\n    예) 0900 → 09:00 으로 자동 변환"));
		intervalGrid = new DataGridView();
		((Control)intervalGrid).Location = new Point(5, 5);
		((Control)intervalGrid).Size = new Size(510, 265);
		intervalGrid.AllowUserToAddRows = false;
		intervalGrid.AllowUserToDeleteRows = false;
		intervalGrid.RowHeadersVisible = false;
		DataGridViewColumnCollection columns4 = intervalGrid.Columns;
		DataGridViewCheckBoxColumn val16 = new DataGridViewCheckBoxColumn();
		((DataGridViewColumn)val16).Name = "Enabled";
		((DataGridViewColumn)val16).HeaderText = "사용";
		((DataGridViewColumn)val16).Width = 50;
		columns4.Add((DataGridViewColumn)(object)val16);
		DataGridViewColumnCollection columns5 = intervalGrid.Columns;
		DataGridViewTextBoxColumn val17 = new DataGridViewTextBoxColumn();
		((DataGridViewColumn)val17).Name = "Minutes";
		((DataGridViewColumn)val17).HeaderText = "몇 분마다";
		((DataGridViewColumn)val17).Width = 80;
		columns5.Add((DataGridViewColumn)(object)val17);
		DataGridViewColumnCollection columns6 = intervalGrid.Columns;
		DataGridViewTextBoxColumn val18 = new DataGridViewTextBoxColumn();
		((DataGridViewColumn)val18).Name = "Message";
		((DataGridViewColumn)val18).HeaderText = "문구";
		((DataGridViewColumn)val18).Width = 360;
		columns6.Add((DataGridViewColumn)(object)val18);
		((Control)val6).Controls.Add((Control)(object)intervalGrid);
		StyleGrid(intervalGrid, IntervalLight, IntervalHeader, IntervalSelect);
		foreach (IntervalAlarm item3 in intervalWorking)
		{
			intervalGrid.Rows.Add(new object[3] { item3.Enabled, item3.IntervalMinutes, item3.Message });
		}
		Button val19 = new Button();
		((Control)val19).Text = "반복 추가";
		((Control)val19).Location = new Point(5, 275);
		((Control)val19).Width = 100;
		btnIntervalAdd = val19;
		((Control)btnIntervalAdd).Click += delegate
		{
			intervalGrid.Rows.Add(new object[3] { true, "60", "잠깐 쉬었다 가요" });
		};
		((Control)val6).Controls.Add((Control)(object)btnIntervalAdd);
		Button val20 = new Button();
		((Control)val20).Text = "선택 삭제";
		((Control)val20).Location = new Point(115, 275);
		((Control)val20).Width = 100;
		btnIntervalDelete = val20;
		((Control)btnIntervalDelete).Click += delegate
		{
			//IL_0019: Unknown result type (might be due to invalid IL or missing references)
			//IL_001f: Expected O, but got Unknown
			foreach (DataGridViewRow item4 in (BaseCollection)intervalGrid.SelectedRows)
			{
				DataGridViewRow val37 = item4;
				if (!val37.IsNewRow)
				{
					intervalGrid.Rows.Remove(val37);
				}
			}
		};
		((Control)val6).Controls.Add((Control)(object)btnIntervalDelete);
		dateGrid = new DataGridView();
		((Control)dateGrid).Location = new Point(5, 5);
		((Control)dateGrid).Size = new Size(510, 265);
		dateGrid.AllowUserToAddRows = false;
		dateGrid.AllowUserToDeleteRows = false;
		dateGrid.RowHeadersVisible = false;
		DataGridViewColumnCollection columns7 = dateGrid.Columns;
		DataGridViewCheckBoxColumn val21 = new DataGridViewCheckBoxColumn();
		((DataGridViewColumn)val21).Name = "Enabled";
		((DataGridViewColumn)val21).HeaderText = "사용";
		((DataGridViewColumn)val21).Width = 50;
		columns7.Add((DataGridViewColumn)(object)val21);
		DataGridViewColumnCollection columns8 = dateGrid.Columns;
		DataGridViewTextBoxColumn val22 = new DataGridViewTextBoxColumn();
		((DataGridViewColumn)val22).Name = "Date";
		((DataGridViewColumn)val22).HeaderText = "날짜 (20261023)";
		((DataGridViewColumn)val22).Width = 125;
		columns8.Add((DataGridViewColumn)(object)val22);
		DataGridViewColumnCollection columns9 = dateGrid.Columns;
		DataGridViewTextBoxColumn val23 = new DataGridViewTextBoxColumn();
		((DataGridViewColumn)val23).Name = "Time";
		((DataGridViewColumn)val23).HeaderText = "시간 (0900)";
		((DataGridViewColumn)val23).Width = 90;
		columns9.Add((DataGridViewColumn)(object)val23);
		DataGridViewColumnCollection columns10 = dateGrid.Columns;
		DataGridViewTextBoxColumn val24 = new DataGridViewTextBoxColumn();
		((DataGridViewColumn)val24).Name = "Memo";
		((DataGridViewColumn)val24).HeaderText = "메모";
		((DataGridViewColumn)val24).Width = 225;
		columns10.Add((DataGridViewColumn)(object)val24);
		((Control)val8).Controls.Add((Control)(object)dateGrid);
		StyleGrid(dateGrid, DateLight, DateHeader, DateSelect);
		AttachDateTimeInput(dateGrid);
		DataGridView obj = dateGrid;
		if (val == null)
		{
			val = (DataGridViewCellFormattingEventHandler)delegate(object s, DataGridViewCellFormattingEventArgs e)
			{
				if (e.RowIndex >= 0)
				{
					string text = Convert.ToString(dateGrid.Rows[e.RowIndex].Cells["Date"].Value ?? "");
					if (text.Length == 10 && string.CompareOrdinal(text, DateTime.Now.ToString("yyyy-MM-dd")) < 0)
					{
						e.CellStyle.ForeColor = Color.Gray;
					}
				}
			};
		}
		obj.CellFormatting += val;
		foreach (DateAlarm item5 in currentDate)
		{
			dateGrid.Rows.Add(new object[4] { item5.Enabled, item5.Date, item5.Time, item5.Memo });
		}
		Button val25 = new Button();
		((Control)val25).Text = "일정 추가";
		((Control)val25).Location = new Point(5, 275);
		((Control)val25).Width = 100;
		btnDateAdd = val25;
		((Control)btnDateAdd).Click += delegate
		{
			dateGrid.Rows.Add(new object[4]
			{
				true,
				DateTime.Now.AddDays(1.0).ToString("yyyy-MM-dd"),
				"09:00",
				"메모를 적어 주세요"
			});
		};
		((Control)val8).Controls.Add((Control)(object)btnDateAdd);
		Button val26 = new Button();
		((Control)val26).Text = "선택 삭제";
		((Control)val26).Location = new Point(115, 275);
		((Control)val26).Width = 100;
		btnDateDelete = val26;
		((Control)btnDateDelete).Click += delegate
		{
			//IL_0019: Unknown result type (might be due to invalid IL or missing references)
			//IL_001f: Expected O, but got Unknown
			foreach (DataGridViewRow item6 in (BaseCollection)dateGrid.SelectedRows)
			{
				DataGridViewRow val37 = item6;
				if (!val37.IsNewRow)
				{
					dateGrid.Rows.Remove(val37);
				}
			}
		};
		((Control)val8).Controls.Add((Control)(object)btnDateDelete);
		((Control)val8).Controls.Add((Control)(object)HintLabel("※ 날짜: 숫자 8자리  예) 20261023 → 2026-10-23\n※ 시간: 숫자 4자리  예) 0900 → 09:00"));
		CheckBox val27 = new CheckBox();
		((Control)val27).Text = "윈도우 시작 시 자동 실행";
		((Control)val27).Location = new Point(12, 393);
		((Control)val27).AutoSize = true;
		val27.Checked = AutoStart.IsEnabled();
		autoStartCheck = val27;
		((Control)this).Controls.Add((Control)(object)autoStartCheck);
		Label val28 = new Label();
		((Control)val28).Text = "알람 빛 테마";
		((Control)val28).Location = new Point(10, 358);
		((Control)val28).AutoSize = true;
		Label val29 = val28;
		((Control)this).Controls.Add((Control)(object)val29);
		ComboBox val30 = new ComboBox();
		((Control)val30).Location = new Point(110, 354);
		((Control)val30).Width = 150;
		val30.DropDownStyle = (ComboBoxStyle)2;
		themeCombo = val30;
		themeCombo.Items.AddRange((object[])EdgeGlowForm.ThemeNames);
		themeCombo.SelectedItem = AppSettings.GlowTheme;
		if (((ListControl)themeCombo).SelectedIndex < 0)
		{
			((ListControl)themeCombo).SelectedIndex = 0;
		}
		((Control)this).Controls.Add((Control)(object)themeCombo);
		Button val31 = new Button();
		((Control)val31).Text = "테스트";
		((Control)val31).Location = new Point(270, 353);
		((Control)val31).Width = 70;
		Button val32 = val31;
		((Control)val32).Click += delegate
		{
			PreviewGlow();
		};
		((Control)this).Controls.Add((Control)(object)val32);
		Label val33 = new Label();
		((Control)val33).Text = "만든이: PJH";
		((Control)val33).Font = new Font("맑은 고딕", 7.5f);
		((Control)val33).ForeColor = Color.FromArgb(150, 150, 150);
		((Control)val33).AutoSize = true;
		((Control)val33).Location = new Point(468, 358);
		Label val34 = val33;
		((Control)this).Controls.Add((Control)(object)val34);
		if (val2 == null)
		{
			val2 = (FormClosedEventHandler)delegate
			{
				if (previewGlow != null)
				{
					previewGlow.HideGlow();
				}
				if (previewGlowTimer != null)
				{
					previewGlowTimer.Stop();
				}
			};
		}
		((Form)this).FormClosed += val2;
		Button val35 = new Button();
		((Control)val35).Text = "저장";
		((Control)val35).Location = new Point(360, 390);
		((Control)val35).Width = 80;
		btnSave = val35;
		((Control)btnSave).Click += delegate
		{
			SaveAndClose();
		};
		((Control)this).Controls.Add((Control)(object)btnSave);
		Button val36 = new Button();
		((Control)val36).Text = "취소";
		((Control)val36).Location = new Point(450, 390);
		((Control)val36).Width = 80;
		btnCancel = val36;
		((Control)btnCancel).Click += delegate
		{
			((Form)this).DialogResult = (DialogResult)2;
			((Form)this).Close();
		};
		((Control)this).Controls.Add((Control)(object)btnCancel);
	}

	private void PreviewGlow()
	{
		//IL_005e: Unknown result type (might be due to invalid IL or missing references)
		//IL_0068: Expected O, but got Unknown
		if (themeCombo.SelectedItem == null)
		{
			return;
		}
		if (previewGlow == null)
		{
			previewGlow = new EdgeGlowForm();
		}
		previewGlow.SetTheme(themeCombo.SelectedItem.ToString());
		previewGlow.ShowGlow(((Control)this).Bounds);
		((Control)this).BringToFront();
		if (previewGlowTimer == null)
		{
			previewGlowTimer = new Timer();
			previewGlowTimer.Interval = 2500;
			previewGlowTimer.Tick += delegate
			{
				previewGlowTimer.Stop();
				if (previewGlow != null)
				{
					previewGlow.HideGlow();
				}
			};
		}
		previewGlowTimer.Stop();
		previewGlowTimer.Start();
	}

	private static string NormalizeTime(string input)
	{
		if (input == null)
		{
			return null;
		}
		string text = input.Trim();
		string[] array = text.Split(new char[4] { ':', '.', ' ', ';' }, StringSplitOptions.RemoveEmptyEntries);
		int result;
		int result2;
		if (array.Length == 2)
		{
			if (!int.TryParse(array[0], out result) || !int.TryParse(array[1], out result2))
			{
				return null;
			}
		}
		else
		{
			if (array.Length != 1 || array[0].Length > 4)
			{
				return null;
			}
			string text2 = array[0];
			if (!int.TryParse(text2, out var result3) || result3 < 0)
			{
				return null;
			}
			if (text2.Length <= 2)
			{
				result = result3;
				result2 = 0;
			}
			else
			{
				result = result3 / 100;
				result2 = result3 % 100;
			}
		}
		if (result < 0 || result > 23 || result2 < 0 || result2 > 59)
		{
			return null;
		}
		return $"{result:00}:{result2:00}";
	}

	private static Label HintLabel(string text)
	{
		//IL_0000: Unknown result type (might be due to invalid IL or missing references)
		//IL_0006: Expected O, but got Unknown
		//IL_003f: Unknown result type (might be due to invalid IL or missing references)
		//IL_0049: Expected O, but got Unknown
		Label val = new Label();
		((Control)val).Text = text;
		((Control)val).Location = new Point(225, 272);
		((Control)val).Size = new Size(295, 32);
		((Control)val).Font = new Font("맑은 고딕", 8.5f);
		((Control)val).ForeColor = Color.FromArgb(70, 70, 70);
		((Control)val).BackColor = Color.Transparent;
		return val;
	}

	private static void AttachDateTimeInput(DataGridView g)
	{
		//IL_001a: Unknown result type (might be due to invalid IL or missing references)
		//IL_0024: Expected O, but got Unknown
		//IL_0031: Unknown result type (might be due to invalid IL or missing references)
		//IL_003b: Expected O, but got Unknown
		g.EditingControlShowing += (DataGridViewEditingControlShowingEventHandler)delegate(object s, DataGridViewEditingControlShowingEventArgs e)
		{
			//IL_0018: Unknown result type (might be due to invalid IL or missing references)
			//IL_0022: Expected O, but got Unknown
			//IL_005a: Unknown result type (might be due to invalid IL or missing references)
			//IL_0064: Expected O, but got Unknown
			Control control = e.Control;
			TextBox val = (TextBox)(object)((control is TextBox) ? control : null);
			if (val != null)
			{
				((Control)val).KeyPress -= new KeyPressEventHandler(DigitsOnlyKeyPress);
				string name = g.CurrentCell.OwningColumn.Name;
				if (name == "Date" || name == "Time")
				{
					((Control)val).KeyPress += new KeyPressEventHandler(DigitsOnlyKeyPress);
					((TextBoxBase)val).MaxLength = ((name == "Date") ? 10 : 5);
				}
				else
				{
					((TextBoxBase)val).MaxLength = 32767;
				}
			}
		};
		g.CellEndEdit += (DataGridViewCellEventHandler)delegate(object s, DataGridViewCellEventArgs e)
		{
			string name = g.Columns[e.ColumnIndex].Name;
			if (!(name != "Date") || !(name != "Time"))
			{
				DataGridViewCell val = g.Rows[e.RowIndex].Cells[e.ColumnIndex];
				string input = Convert.ToString(val.Value ?? "");
				string text = ((name == "Date") ? NormalizeDate(input) : NormalizeTime(input));
				if (text != null)
				{
					val.Value = text;
					val.ErrorText = "";
					val.Style.BackColor = Color.Empty;
				}
				else
				{
					val.ErrorText = ((name == "Date") ? "날짜는 20261023 처럼 숫자 8자리로 입력해 주세요" : "시간은 0900 처럼 숫자 4자리로 입력해 주세요");
					val.Style.BackColor = Color.FromArgb(255, 205, 205);
				}
			}
		};
	}

	private static void DigitsOnlyKeyPress(object sender, KeyPressEventArgs e)
	{
		if (!char.IsControl(e.KeyChar) && !char.IsDigit(e.KeyChar))
		{
			e.Handled = true;
		}
	}

	private static void StyleGrid(DataGridView g, Color light, Color header, Color select)
	{
		//IL_002b: Unknown result type (might be due to invalid IL or missing references)
		//IL_0035: Expected O, but got Unknown
		g.BackgroundColor = light;
		g.EnableHeadersVisualStyles = false;
		g.ColumnHeadersDefaultCellStyle.BackColor = header;
		g.ColumnHeadersDefaultCellStyle.Font = new Font("맑은 고딕", 9f, (FontStyle)1);
		g.DefaultCellStyle.BackColor = Color.White;
		g.AlternatingRowsDefaultCellStyle.BackColor = light;
		g.DefaultCellStyle.SelectionBackColor = select;
		g.DefaultCellStyle.SelectionForeColor = Color.White;
		g.SelectionMode = (DataGridViewSelectionMode)1;
	}

	private static string NormalizeDate(string input)
	{
		if (input == null)
		{
			return null;
		}
		string text = input.Trim().Replace("년", " ").Replace("월", " ")
			.Replace("일", " ");
		string[] array = text.Split(new char[4] { '-', '/', '.', ' ' }, StringSplitOptions.RemoveEmptyEntries);
		int result = -1;
		int result2;
		int result3;
		if (array.Length == 3)
		{
			if (!int.TryParse(array[0], out result) || !int.TryParse(array[1], out result2) || !int.TryParse(array[2], out result3))
			{
				return null;
			}
			if (result < 100)
			{
				result += 2000;
			}
		}
		else if (array.Length == 2)
		{
			if (!int.TryParse(array[0], out result2) || !int.TryParse(array[1], out result3))
			{
				return null;
			}
		}
		else
		{
			if (array.Length != 1)
			{
				return null;
			}
			if (!int.TryParse(array[0], out var result4) || result4 < 0)
			{
				return null;
			}
			if (array[0].Length == 8)
			{
				result = result4 / 10000;
				result2 = result4 / 100 % 100;
				result3 = result4 % 100;
			}
			else
			{
				if (array[0].Length != 3 && array[0].Length != 4)
				{
					return null;
				}
				result2 = result4 / 100;
				result3 = result4 % 100;
			}
		}
		if (result2 < 1 || result2 > 12 || result3 < 1 || result3 > 31)
		{
			return null;
		}
		if (result < 0)
		{
			result = DateTime.Today.Year;
			if (result3 <= DateTime.DaysInMonth(result, result2) && new DateTime(result, result2, result3) < DateTime.Today)
			{
				result++;
			}
		}
		if (result < 2000 || result > 2100 || result3 > DateTime.DaysInMonth(result, result2))
		{
			return null;
		}
		return new DateTime(result, result2, result3).ToString("yyyy-MM-dd");
	}

	private void SaveAndClose()
	{
		//IL_0024: Unknown result type (might be due to invalid IL or missing references)
		//IL_002a: Expected O, but got Unknown
		//IL_0196: Unknown result type (might be due to invalid IL or missing references)
		//IL_019d: Expected O, but got Unknown
		//IL_00e9: Unknown result type (might be due to invalid IL or missing references)
		//IL_01f5: Unknown result type (might be due to invalid IL or missing references)
		//IL_02d5: Unknown result type (might be due to invalid IL or missing references)
		//IL_02dc: Expected O, but got Unknown
		//IL_035c: Unknown result type (might be due to invalid IL or missing references)
		//IL_0385: Unknown result type (might be due to invalid IL or missing references)
		List<AlarmItem> list = new List<AlarmItem>();
		foreach (DataGridViewRow item in (IEnumerable)grid.Rows)
		{
			DataGridViewRow val = item;
			if (!val.IsNewRow)
			{
				string text = Convert.ToString(val.Cells["Time"].Value ?? "").Trim();
				string text2 = Convert.ToString(val.Cells["Type"].Value ?? "").Trim();
				if (string.IsNullOrEmpty(text2) || Array.IndexOf(AlarmItem.Types, text2) < 0)
				{
					text2 = "일반";
				}
				string message = Convert.ToString(val.Cells["Message"].Value ?? "").Trim();
				string text3 = NormalizeTime(text);
				if (text3 == null)
				{
					MessageBox.Show("시간은 0900 처럼 숫자 4자리로 입력해주세요. (자동으로 09:00 이 돼요)\n잘못된 값: " + text, "입력 오류");
					return;
				}
				text = text3;
				bool enabled = Convert.ToBoolean(val.Cells["Enabled"].Value ?? ((object)false));
				list.Add(new AlarmItem
				{
					Enabled = enabled,
					Time = text,
					Type = text2,
					Message = message
				});
			}
		}
		List<IntervalAlarm> list2 = new List<IntervalAlarm>();
		foreach (DataGridViewRow item2 in (IEnumerable)intervalGrid.Rows)
		{
			DataGridViewRow val2 = item2;
			if (!val2.IsNewRow)
			{
				string text4 = Convert.ToString(val2.Cells["Minutes"].Value ?? "").Trim();
				if (!int.TryParse(text4, out var result) || result <= 0)
				{
					MessageBox.Show("반복 간격은 1 이상의 숫자(분)로 입력해주세요.\n잘못된 값: " + text4, "입력 오류");
					return;
				}
				string type = "일반";
				string message2 = Convert.ToString(val2.Cells["Message"].Value ?? "").Trim();
				bool enabled2 = Convert.ToBoolean(val2.Cells["Enabled"].Value ?? ((object)false));
				list2.Add(new IntervalAlarm
				{
					Enabled = enabled2,
					IntervalMinutes = result,
					Type = type,
					Message = message2
				});
			}
		}
		List<DateAlarm> list3 = new List<DateAlarm>();
		foreach (DataGridViewRow item3 in (IEnumerable)dateGrid.Rows)
		{
			DataGridViewRow val3 = item3;
			if (!val3.IsNewRow)
			{
				string text5 = Convert.ToString(val3.Cells["Date"].Value ?? "").Trim();
				string text6 = Convert.ToString(val3.Cells["Time"].Value ?? "").Trim();
				string text7 = NormalizeDate(text5);
				if (text7 == null)
				{
					MessageBox.Show("날짜는 20261023 처럼 숫자 8자리로 입력해주세요. (자동으로 2026-10-23 이 돼요)\n잘못된 값: " + text5, "입력 오류");
					return;
				}
				string text8 = NormalizeTime(text6);
				if (text8 == null)
				{
					MessageBox.Show("시간은 0900 처럼 숫자 4자리로 입력해주세요. (자동으로 09:00 이 돼요)\n잘못된 값: " + text6, "입력 오류");
					return;
				}
				string memo = Convert.ToString(val3.Cells["Memo"].Value ?? "").Trim();
				bool enabled3 = Convert.ToBoolean(val3.Cells["Enabled"].Value ?? ((object)false));
				list3.Add(new DateAlarm
				{
					Enabled = enabled3,
					Date = text7,
					Time = text8,
					Memo = memo
				});
			}
		}
		if (themeCombo.SelectedItem != null)
		{
			AppSettings.GlowTheme = themeCombo.SelectedItem.ToString();
			AppSettings.Save();
		}
		if (autoStartCheck.Checked != AutoStart.IsEnabled())
		{
			AutoStart.Set(autoStartCheck.Checked);
		}
		SaveCalendarTab();
		Result = list;
		IntervalResult = list2;
		DateResult = list3;
		((Form)this).DialogResult = (DialogResult)1;
		((Form)this).Close();
	}

	// ───────── 달력 알람 탭 (업무보조 달력과 같은 설정을 보고 고친다) ─────────
	private static readonly string[] CalRangeNames = new string[5] { "오늘까지", "내일까지", "3일 뒤까지", "일주일 뒤까지", "한 달 뒤까지" };

	private static readonly int[] CalRangeDays = new int[5] { 0, 1, 3, 7, 30 };

	private static readonly int[] CalEveryHours = new int[4] { 1, 2, 3, 4 };

	private static readonly int[] CalLaterHours = new int[6] { 1, 2, 3, 4, 6, 8 };

	private CheckBox calCheckin;

	private CheckBox calWork;

	private CheckBox calAlerts;

	private ComboBox calEvery;

	private ComboBox calRange;

	private ComboBox calLater;

	private Label calMuted;

	private CheckBox calBrief;

	private ComboBox calBriefTime;

	private ComboBox calWorkType;

	private CheckBox calReact;

	private static readonly string[] BriefTimes = new string[12] { "06:00", "06:30", "07:00", "07:30", "08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30" };

	private static readonly string[] WorkTypeNames = new string[2] { "일근 (평일 출근)", "3교대 (내 팀 근무일)" };

	private bool calUnmute;

	private static string Get(Dictionary<string, string> d, string key, string def)
	{
		string v;
		return d.TryGetValue(key, out v) ? v : def;
	}

	private static ComboBox MakeCombo(Control parent, int x, int y, int width, string[] items, int index)
	{
		ComboBox c = new ComboBox();
		c.DropDownStyle = ComboBoxStyle.DropDownList;
		c.Location = new Point(x, y);
		c.Width = width;
		c.Items.AddRange(items);
		c.SelectedIndex = Math.Max(0, Math.Min(items.Length - 1, index));
		parent.Controls.Add(c);
		return c;
	}

	private static Label MakeLabel(Control parent, string text, int x, int y, int width)
	{
		Label l = new Label();
		l.Text = text;
		l.Location = new Point(x, y + 3);
		l.Width = width;
		l.AutoSize = false;
		parent.Controls.Add(l);
		return l;
	}

	private void BuildCalendarTab(TabPage page)
	{
		Dictionary<string, string> st = CalendarBridge.ReadSettings();
		calCheckin = new CheckBox();
		calCheckin.Text = "달력의 할 일을 주기적으로 '이 일 했어요?' 하고 물어보기";
		calCheckin.Location = new Point(12, 8);
		calCheckin.Width = 490;
		calCheckin.Checked = Get(st, "checkin", "1") == "1";
		page.Controls.Add(calCheckin);
		MakeLabel(page, "물어보는 간격", 30, 36, 88);
		calEvery = MakeCombo(page, 120, 36, 70, Array.ConvertAll(CalEveryHours, (int h) => h + "시간"), Array.IndexOf(CalEveryHours, int.Parse(Get(st, "every", "2"))));
		MakeLabel(page, "확인할 범위", 210, 36, 75);
		calRange = MakeCombo(page, 288, 36, 110, CalRangeNames, Array.IndexOf(CalRangeDays, int.Parse(Get(st, "range", "1"))));
		MakeLabel(page, "[진행중] 누르면", 30, 66, 100);
		calLater = MakeCombo(page, 132, 66, 70, Array.ConvertAll(CalLaterHours, (int h) => h + "시간"), Array.IndexOf(CalLaterHours, int.Parse(Get(st, "progress", "4"))));
		MakeLabel(page, "뒤에 다시 물어보기", 208, 66, 140);
		calWork = new CheckBox();
		calWork.Text = "09시 ~ 18시 사이에만 물어보기";
		calWork.Location = new Point(30, 90);
		calWork.Width = 300;
		calWork.Checked = Get(st, "workhours", "1") == "1";
		page.Controls.Add(calWork);
		calAlerts = new CheckBox();
		calAlerts.Text = "기한 알림(3일 전 · 하루 전 · 당일 · 지남)도 병아리가 전하기";
		calAlerts.Location = new Point(12, 112);
		calAlerts.Width = 490;
		calAlerts.Checked = Get(st, "alerts", "1") == "1";
		page.Controls.Add(calAlerts);
		calBrief = new CheckBox();
		calBrief.Text = "아침 브리핑 (근무하는 날)";
		calBrief.Location = new Point(12, 136);
		calBrief.Width = 175;
		calBrief.Checked = Get(st, "brief", "1") == "1";
		page.Controls.Add(calBrief);
		calBriefTime = MakeCombo(page, 190, 136, 66, BriefTimes, Math.Max(0, Array.IndexOf(BriefTimes, Get(st, "brief_time", "09:00"))));
		MakeLabel(page, "근무 형태", 268, 139, 60);
		calWorkType = MakeCombo(page, 330, 136, 180, WorkTypeNames, (Get(st, "work_type", "day") == "shift") ? 1 : 0);
		calReact = new CheckBox();
		calReact.Text = "병아리 반응 (많이 처리하면 축하 춤 · 기한 지난 일이 쌓이면 걱정)";
		calReact.Location = new Point(12, 160);
		calReact.Width = 490;
		calReact.Checked = Get(st, "react", "1") == "1";
		page.Controls.Add(calReact);
		MakeLabel(page, "지금 달력에서 챙길 일", 12, 188, 300).Font = new Font("맑은 고딕", 9f, FontStyle.Bold);
		ListBox list = new ListBox();
		list.Location = new Point(12, 208);
		list.Size = new Size(500, 56);
		list.HorizontalScrollbar = true;
		foreach (string[] it in CalendarBridge.ReadUpcoming())
		{
			list.Items.Add(it[0] + "   " + it[1] + ((it.Length > 2 && it[2].Length > 0) ? ("   (" + it[2] + ")") : ""));
		}
		if (list.Items.Count == 0)
		{
			list.Items.Add(CalendarBridge.Linked ? "  챙길 일이 없어요. 잘하고 있어요!" : "  업무보조 달력과 아직 연결되지 않았어요. 달력에서 [병아리대원 출동]을 눌러 주세요.");
		}
		page.Controls.Add(list);
		calMuted = MakeLabel(page, "알람 끈 일: " + Get(st, "muted", "0") + "개", 12, 272, 150);
		Button unmute = new Button();
		unmute.Text = "모두 다시 켜기";
		unmute.Location = new Point(165, 268);
		unmute.Width = 110;
		unmute.Click += delegate
		{
			calUnmute = true;
			calMuted.Text = "알람 끈 일: 0개 (저장하면 다시 물어봐요)";
		};
		page.Controls.Add(unmute);
		MakeLabel(page, "병아리를 한 번 누르면 말로 메모를 달력에 적어요", 284, 272, 230).ForeColor = Color.FromArgb(110, 110, 110);
	}

	private void SaveCalendarTab()
	{
		if (calCheckin == null)
		{
			return;
		}
		Dictionary<string, string> st = CalendarBridge.ReadSettings();
		st["checkin"] = calCheckin.Checked ? "1" : "0";
		st["every"] = CalEveryHours[Math.Max(0, calEvery.SelectedIndex)].ToString();
		st["range"] = CalRangeDays[Math.Max(0, calRange.SelectedIndex)].ToString();
		st["progress"] = CalLaterHours[Math.Max(0, calLater.SelectedIndex)].ToString();
		st["workhours"] = calWork.Checked ? "1" : "0";
		st["alerts"] = calAlerts.Checked ? "1" : "0";
		st["brief"] = calBrief.Checked ? "1" : "0";
		st["brief_time"] = BriefTimes[Math.Max(0, calBriefTime.SelectedIndex)];
		st["work_type"] = (calWorkType.SelectedIndex == 1) ? "shift" : "day";
		st["react"] = calReact.Checked ? "1" : "0";
		if (calUnmute)
		{
			st["unmute_all"] = "1";
		}
		st["changed_by"] = "chick";
		CalendarBridge.WriteSettings(st);
	}
}
