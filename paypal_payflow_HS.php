<?php
/*
  $Id$

  osCommerce, Open Source E-Commerce Solutions
  http://www.oscommerce.com

  PayPal	
  Released under the Apache 2.0 License - Paypal
  @aurthor DriveDev (rock mutchler)
*/
?>
<div align="center">
<form action="https://payflowlink.paypal.com/" method="post" name='pphs' id='pphs'>
<?php
	foreach ($_GET as $key => $value){
?>
	<input type="hidden" name="<?php print $key;?>" value="<?php print $value;?>">
<?php 
	}
?>
</form>
<!-- now send the form! -->
<script type='text/javascript'>document.pphs.submit();</script>
</div>
