using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Drawing.Text;
using System.Linq;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace MyMascot;

public class ChoiceBubbleForm : Form
{
	private const int CloudH = 58;

	private const int Gap = 2;

	private readonly string[] options;

	private readonly Action<int> onPick;

	private readonly List<RectangleF> cores;

	private int hover;

	private readonly Timer autoClose;

	private static readonly Color HoverFill = Color.FromArgb(255, 255, 244, 200);

	protected override CreateParams CreateParams
	{
		get
		{
			CreateParams createParams = base.CreateParams;
			createParams.ExStyle |= 0x80080;
			return createParams;
		}
	}

	protected override bool ShowWithoutActivation => true;

	[DllImport("user32.dll", SetLastError = true)]
	private static extern bool UpdateLayeredWindow(IntPtr hwnd, IntPtr hdcDst, ref MascotForm.POINTAPI pptDst, ref MascotForm.SIZEAPI psize, IntPtr hdcSrc, ref MascotForm.POINTAPI pptSrc, int crKey, ref MascotForm.BLENDFUNCTION pblend, int dwFlags);

	[DllImport("user32.dll")]
	private static extern IntPtr GetDC(IntPtr hWnd);

	[DllImport("user32.dll")]
	private static extern int ReleaseDC(IntPtr hWnd, IntPtr hDC);

	[DllImport("gdi32.dll")]
	private static extern IntPtr CreateCompatibleDC(IntPtr hDC);

	[DllImport("gdi32.dll")]
	private static extern IntPtr SelectObject(IntPtr hDC, IntPtr hObject);

	[DllImport("gdi32.dll")]
	private static extern bool DeleteObject(IntPtr hObject);

	[DllImport("gdi32.dll")]
	private static extern bool DeleteDC(IntPtr hDC);

	public ChoiceBubbleForm(string[] options, Action<int> onPick, int autoCloseMs = 10000)
	{
		//IL_005a: Unknown result type (might be due to invalid IL or missing references)
		//IL_0060: Expected O, but got Unknown
		//IL_0093: Unknown result type (might be due to invalid IL or missing references)
		//IL_009d: Expected O, but got Unknown
		//IL_0161: Unknown result type (might be due to invalid IL or missing references)
		//IL_0168: Expected O, but got Unknown
		//IL_01a4: Unknown result type (might be due to invalid IL or missing references)
		//IL_01ab: Expected O, but got Unknown
		//IL_0195: Unknown result type (might be due to invalid IL or missing references)
		//IL_019c: Expected O, but got Unknown
		//IL_01f4: Unknown result type (might be due to invalid IL or missing references)
		//IL_01fb: Expected O, but got Unknown
		MouseEventHandler val = null;
		MouseEventHandler val2 = null;
		FormClosedEventHandler val3 = null;
		cores = new List<RectangleF>();
		hover = -1;
		this.options = options;
		this.onPick = onPick;
		((Form)this).FormBorderStyle = (FormBorderStyle)0;
		((Form)this).ShowInTaskbar = false;
		((Form)this).TopMost = true;
		((Control)this).Cursor = Cursors.Hand;
		int num = 13;
		Bitmap val4 = new Bitmap(1, 1);
		try
		{
			Graphics g = Graphics.FromImage((Image)(object)val4);
			try
			{
				Font font = new Font("맑은 고딕", 10f, (FontStyle)1);
				try
				{
					float num2 = options.Max((string o) => g.MeasureString(o, font).Width);
					((Control)this).Width = Math.Max(130, (int)num2 + 30 + 2 * num);
				}
				finally
				{
					if (font != null)
					{
						((IDisposable)font).Dispose();
					}
				}
			}
			finally
			{
				if (g != null)
				{
					((IDisposable)g).Dispose();
				}
			}
		}
		finally
		{
			((IDisposable)val4)?.Dispose();
		}
		((Control)this).Height = options.Length * 60;
		for (int num3 = 0; num3 < options.Length; num3++)
		{
			cores.Add(new RectangleF(num, num3 * 60 + num, ((Control)this).Width - 2 * num, 58 - 2 * num));
		}
		if (val == null)
		{
			val = (MouseEventHandler)delegate(object s, MouseEventArgs e)
			{
				int num4 = HitTest(e.Location);
				if (num4 != hover)
				{
					hover = num4;
					Redraw();
				}
			};
		}
		((Control)this).MouseMove += val;
		((Control)this).MouseLeave += delegate
		{
			if (hover != -1)
			{
				hover = -1;
				Redraw();
			}
		};
		if (val2 == null)
		{
			val2 = (MouseEventHandler)delegate(object s, MouseEventArgs e)
			{
				//IL_0012: Unknown result type (might be due to invalid IL or missing references)
				//IL_001c: Invalid comparison between Unknown and I4
				int num4 = HitTest(e.Location);
				if (num4 >= 0 && (int)e.Button == 1048576)
				{
					((Form)this).Close();
					if (this.onPick != null)
					{
						this.onPick(num4);
					}
				}
			};
		}
		((Control)this).MouseUp += val2;
		Timer val5 = new Timer();
		val5.Interval = autoCloseMs;
		autoClose = val5;
		autoClose.Tick += delegate
		{
			autoClose.Stop();
			((Form)this).Close();
		};
		autoClose.Start();
		if (val3 == null)
		{
			val3 = (FormClosedEventHandler)delegate
			{
				((Component)(object)autoClose).Dispose();
			};
		}
		((Form)this).FormClosed += val3;
	}

	private int HitTest(Point p)
	{
		for (int i = 0; i < cores.Count; i++)
		{
			if (RectangleF.Inflate(cores[i], 11f, 11f).Contains(p))
			{
				return i;
			}
		}
		return -1;
	}

	public void ShowNear(Rectangle character)
	{
		Rectangle workingArea = Screen.FromRectangle(character).WorkingArea;
		int num = character.Left - ((Control)this).Width + 15;
		if (num < workingArea.Left)
		{
			num = character.Right - 15;
		}
		int y = Math.Max(workingArea.Top, Math.Min(workingArea.Bottom - ((Control)this).Height, character.Top + 20));
		((Form)this).Location = new Point(num, y);
		Redraw();
		((Control)this).Show();
	}

	private void Redraw()
	{
		//IL_0011: Unknown result type (might be due to invalid IL or missing references)
		//IL_0017: Expected O, but got Unknown
		//IL_0029: Unknown result type (might be due to invalid IL or missing references)
		//IL_002f: Expected O, but got Unknown
		//IL_003f: Unknown result type (might be due to invalid IL or missing references)
		//IL_0045: Expected O, but got Unknown
		//IL_0045: Unknown result type (might be due to invalid IL or missing references)
		//IL_004c: Expected O, but got Unknown
		Bitmap val = new Bitmap(((Control)this).Width, ((Control)this).Height, (PixelFormat)2498570);
		try
		{
			Graphics val2 = Graphics.FromImage((Image)(object)val);
			try
			{
				Font val3 = new Font("맑은 고딕", 10f, (FontStyle)1);
				try
				{
					SolidBrush val4 = new SolidBrush(Color.FromArgb(255, 55, 45, 40));
					try
					{
						StringFormat val5 = new StringFormat();
						val5.Alignment = (StringAlignment)1;
						val5.LineAlignment = (StringAlignment)1;
						StringFormat val6 = val5;
						try
						{
							val2.Clear(Color.Transparent);
							val2.SmoothingMode = (SmoothingMode)4;
							val2.TextRenderingHint = (TextRenderingHint)3;
							for (int i = 0; i < options.Length; i++)
							{
								RectangleF rectangleF = cores[i];
								SpeechBubbleForm.DrawBlob(val2, SpeechBubbleForm.CloudShapes(rectangleF), SpeechBubbleForm.CloudPuffPath(rectangleF), 2.2f, (i == hover) ? HoverFill : Color.White);
								val2.DrawString(options[i], val3, (Brush)(object)val4, rectangleF, val6);
							}
						}
						finally
						{
							((IDisposable)val6)?.Dispose();
						}
					}
					finally
					{
						((IDisposable)val4)?.Dispose();
					}
				}
				finally
				{
					((IDisposable)val3)?.Dispose();
				}
			}
			finally
			{
				((IDisposable)val2)?.Dispose();
			}
			SetBitmap(val);
		}
		finally
		{
			((IDisposable)val)?.Dispose();
		}
	}

	private void SetBitmap(Bitmap bitmap)
	{
		IntPtr dC = GetDC(IntPtr.Zero);
		IntPtr intPtr = CreateCompatibleDC(dC);
		IntPtr intPtr2 = IntPtr.Zero;
		IntPtr hObject = IntPtr.Zero;
		try
		{
			intPtr2 = bitmap.GetHbitmap(Color.FromArgb(0));
			hObject = SelectObject(intPtr, intPtr2);
			MascotForm.SIZEAPI psize = new MascotForm.SIZEAPI(((Image)bitmap).Width, ((Image)bitmap).Height);
			MascotForm.POINTAPI pptSrc = new MascotForm.POINTAPI(0, 0);
			MascotForm.POINTAPI pptDst = new MascotForm.POINTAPI(((Control)this).Left, ((Control)this).Top);
			MascotForm.BLENDFUNCTION pblend = new MascotForm.BLENDFUNCTION
			{
				BlendOp = 0,
				BlendFlags = 0,
				SourceConstantAlpha = byte.MaxValue,
				AlphaFormat = 1
			};
			UpdateLayeredWindow(((Control)this).Handle, dC, ref pptDst, ref psize, intPtr, ref pptSrc, 0, ref pblend, 2);
		}
		finally
		{
			ReleaseDC(IntPtr.Zero, dC);
			if (intPtr2 != IntPtr.Zero)
			{
				SelectObject(intPtr, hObject);
				DeleteObject(intPtr2);
			}
			DeleteDC(intPtr);
		}
	}
}
