using System;
using System.Drawing;
using System.Windows.Forms;

namespace MyMascot;

public class AlarmDialogForm : Form
{
	public Action OnConfirm;

	public AlarmDialogForm(string title, string message)
	{
		//IL_0048: Unknown result type (might be due to invalid IL or missing references)
		//IL_004e: Expected O, but got Unknown
		//IL_0061: Unknown result type (might be due to invalid IL or missing references)
		//IL_006b: Expected O, but got Unknown
		//IL_00a0: Unknown result type (might be due to invalid IL or missing references)
		//IL_00a6: Expected O, but got Unknown
		((Control)this).Text = title;
		((Control)this).Width = 380;
		((Control)this).Height = 190;
		((Form)this).StartPosition = (FormStartPosition)1;
		((Form)this).FormBorderStyle = (FormBorderStyle)3;
		((Form)this).MaximizeBox = false;
		((Form)this).MinimizeBox = false;
		((Form)this).TopMost = true;
		Label val = new Label();
		((Control)val).Text = message;
		((Control)val).Font = new Font("맑은 고딕", 12f, (FontStyle)1);
		val.TextAlign = (ContentAlignment)32;
		((Control)val).Location = new Point(15, 20);
		((Control)val).Size = new Size(350, 80);
		((Control)this).Controls.Add((Control)(object)val);
		Button val2 = new Button();
		((Control)val2).Text = "확인";
		((Control)val2).Size = new Size(100, 36);
		((Control)val2).Location = new Point(140, 110);
		EventHandler eventHandler = delegate
		{
			if (OnConfirm != null)
			{
				OnConfirm();
			}
			((Form)this).Close();
		};
		((Control)val2).Click += eventHandler;
		((Control)this).Controls.Add((Control)(object)val2);
		((Form)this).AcceptButton = (IButtonControl)(object)val2;
	}
}
