using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace MyMascot;

public class EdgeGlowForm : Form
{
	private const int WS_EX_LAYERED = 524288;

	private const int WS_EX_TRANSPARENT = 32;

	private const int WS_EX_TOOLWINDOW = 128;

	private const int PulseTicks = 16;

	private const int Spread = 130;

	public static readonly string[] ThemeNames = new string[4] { "노을", "오로라", "바다", "하늘" };

	private string theme = "노을";

	private Timer pulseTimer;

	private int pulseTick;

	private Size targetSize;

	protected override CreateParams CreateParams
	{
		get
		{
			CreateParams createParams = base.CreateParams;
			createParams.ExStyle |= 0x800A0;
			return createParams;
		}
	}

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

	public EdgeGlowForm()
	{
		((Form)this).StartPosition = FormStartPosition.Manual;   // 처음 띄울 때 윈도우가 위치를 바꾸지 않게 (로프 위치 어긋남 수정)
		((Form)this).FormBorderStyle = (FormBorderStyle)0;
		((Form)this).ShowInTaskbar = false;
		((Form)this).TopMost = true;
	}

	public void SetTheme(string t)
	{
		theme = t;
	}

	public void ShowGlow(Rectangle target)
	{
		//IL_004a: Unknown result type (might be due to invalid IL or missing references)
		//IL_0054: Expected O, but got Unknown
		targetSize = target.Size;
		((Control)this).Bounds = Rectangle.Inflate(target, 130, 130);
		pulseTick = 0;
		Redraw(1.0);
		((Control)this).Show();
		if (pulseTimer == null)
		{
			pulseTimer = new Timer();
			pulseTimer.Interval = 100;
			pulseTimer.Tick += delegate
			{
				pulseTick++;
				if (pulseTick > 16)
				{
					pulseTimer.Stop();
					Redraw(0.6);
				}
				else
				{
					double intensity = 0.65 + 0.35 * Math.Abs(Math.Sin((double)pulseTick * 0.5));
					Redraw(intensity);
				}
			};
		}
		pulseTimer.Stop();
		pulseTimer.Start();
	}

	public void FollowTarget(Rectangle target)
	{
		if (((Control)this).Visible)
		{
			if (target.Size != targetSize)
			{
				ShowGlow(target);
			}
			else
			{
				((Form)this).Location = new Point(target.X - 130, target.Y - 130);
			}
		}
	}

	public void HideGlow()
	{
		if (pulseTimer != null)
		{
			pulseTimer.Stop();
		}
		((Control)this).Hide();
	}

	private Color[] ThemeColors()
	{
		return theme switch
		{
			"오로라" => new Color[4]
			{
				Color.FromArgb(18, 16, 48),
				Color.FromArgb(120, 70, 200),
				Color.FromArgb(90, 150, 230),
				Color.FromArgb(205, 205, 255)
			}, 
			"바다" => new Color[4]
			{
				Color.FromArgb(15, 120, 140),
				Color.FromArgb(70, 195, 200),
				Color.FromArgb(175, 228, 215),
				Color.FromArgb(248, 238, 218)
			}, 
			"하늘" => new Color[4]
			{
				Color.FromArgb(55, 125, 200),
				Color.FromArgb(125, 180, 225),
				Color.FromArgb(205, 225, 242),
				Color.FromArgb(250, 250, 252)
			}, 
			_ => new Color[4]
			{
				Color.FromArgb(85, 40, 75),
				Color.FromArgb(205, 50, 45),
				Color.FromArgb(235, 110, 30),
				Color.FromArgb(255, 195, 60)
			}, 
		};
	}

	private void Redraw(double intensity)
	{
		//IL_0024: Unknown result type (might be due to invalid IL or missing references)
		//IL_002a: Expected O, but got Unknown
		//IL_00c4: Unknown result type (might be due to invalid IL or missing references)
		//IL_00cb: Expected O, but got Unknown
		//IL_0126: Unknown result type (might be due to invalid IL or missing references)
		//IL_012d: Expected O, but got Unknown
		if (((Control)this).Width <= 0 || ((Control)this).Height <= 0)
		{
			return;
		}
		Bitmap val = new Bitmap(((Control)this).Width, ((Control)this).Height, (PixelFormat)2498570);
		try
		{
			Graphics val2 = Graphics.FromImage((Image)(object)val);
			try
			{
				val2.Clear(Color.Transparent);
				val2.SmoothingMode = (SmoothingMode)4;
				val2.SetClip(new Rectangle(130, 130, targetSize.Width, targetSize.Height), (CombineMode)4);
				Color[] array = ThemeColors();
				int num = (int)(200.0 * Math.Max(0.0, Math.Min(1.0, intensity)));
				GraphicsPath val3 = RoundedRect(new Rectangle(0, 0, ((Control)this).Width - 1, ((Control)this).Height - 1), 130);
				try
				{
					PathGradientBrush val4 = new PathGradientBrush(val3);
					try
					{
						val4.CenterPoint = new PointF((float)((Control)this).Width / 2f, (float)((Control)this).Height / 2f);
						val4.FocusScales = new PointF((float)targetSize.Width / (float)((Control)this).Width, (float)targetSize.Height / (float)((Control)this).Height);
						ColorBlend val5 = new ColorBlend(5);
						val5.Colors = new Color[5]
						{
							Color.FromArgb(0, array[0]),
							Color.FromArgb(num * 25 / 100, array[0]),
							Color.FromArgb(num * 55 / 100, array[1]),
							Color.FromArgb(num * 85 / 100, array[2]),
							Color.FromArgb(num, array[3])
						};
						val5.Positions = new float[5] { 0f, 0.3f, 0.6f, 0.85f, 1f };
						val4.InterpolationColors = val5;
						val2.FillPath((Brush)(object)val4, val3);
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

	private static GraphicsPath RoundedRect(Rectangle r, int radius)
	{
		//IL_001c: Unknown result type (might be due to invalid IL or missing references)
		//IL_0022: Expected O, but got Unknown
		int num = Math.Min(radius * 2, Math.Min(r.Width, r.Height));
		GraphicsPath val = new GraphicsPath();
		val.AddArc(r.Left, r.Top, num, num, 180f, 90f);
		val.AddArc(r.Right - num, r.Top, num, num, 270f, 90f);
		val.AddArc(r.Right - num, r.Bottom - num, num, num, 0f, 90f);
		val.AddArc(r.Left, r.Bottom - num, num, num, 90f, 90f);
		val.CloseFigure();
		return val;
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
