<?php
/**
 * osCommerce Online Merchant
 * 
 * @copyright Copyright (c) 2011 osCommerce; http://www.oscommerce.com
 * @license BSD License; http://www.oscommerce.com/bsdlicense.txt
 */

  namespace osCommerce\OM\Core\Site\Admin\Module\Payment;

  use osCommerce\OM\Core\OSCOM;
  use osCommerce\OM\Core\Registry;

/**
 * The administration side of the Paypal Express Checkout payment module
 */

  class PayPalPayflowHosted extends \osCommerce\OM\Core\Site\Admin\PaymentModuleAbstract {

/**
 * The administrative title of the payment module
 *
 * @var string
 * @access protected
 */

    protected $_title;

/**
 * The administrative description of the payment module
 *
 * @var string
 * @access protected
 */

    protected $_description;

/**
 * The developers name
 *
 * @var string
 * @access protected
 */

    protected $_author_name = 'Paypal';

/**
 * The developers address
 *
 * @var string
 * @access protected
 */

    protected $_author_www = 'http://www.paypal.com';

/**
 * The status of the module
 *
 * @var boolean
 * @access protected
 */

    protected $_status = false;

/**
 * Initialize module
 *
 * @access protected
 */

    protected function initialize() {
      $this->_title = OSCOM::getDef('paypal_payflow_hosted_title');
      $this->_description = OSCOM::getDef('paypal_payflow_hosted_description');
      $this->_status = (defined('MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_CHECKOUT_STATUS') && (MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_CHECKOUT_STATUS == '1') ? true : false);
      $this->_sort_order = (defined('MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_CHECKOUT_SORT_ORDER') ? MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_CHECKOUT_SORT_ORDER : 0);
    }

/**
 * Checks to see if the module has been installed
 *
 * @access public
 * @return boolean
 */

    public function isInstalled() {
      return defined('MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_CHECKOUT_STATUS');
    }

/**
 * Installs the module
 *
 * @access public
 * @see \osCommerce\OM\Core\Site\Admin\PaymentModuleAbstract::install()
 */

    public function install() {
      parent::install();

      $data = array(array('title' => 'Enable Payflow',
                          'key' => 'MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_CHECKOUT_STATUS',
                          'value' => '-1',
                          'description' => 'Do you want to accept PayPal Payflow payments?',
                          'group_id' => '6',
                          'use_function' => 'osc_cfg_use_get_boolean_value',
                          'set_function' => 'osc_cfg_set_boolean_value(array(1, -1))'),
                    array('title' => 'VENDOR',
                          'key' => 'MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_CHECKOUT_VENDOR',
                          'value' => '',
                          'description' => 'Your merchant login ID that you created when you registered for the Website Payments account.',
                          'group_id' => '6'),
                    array('title' => 'USER',
                          'key' => 'MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_USER',
                          'value' => '',
                          'description' => 'If you set up one or more additional users on the account, this value is the ID of the user authorised to process transactions. If, however, you have not set up additional users on the account, USER has the same value as VENDOR.',
                          'group_id' => '6'),
                    array('title' => 'PASSWORD',
                          'key' => 'MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_PASSWORD',
                          'value' => '',
                          'description' => 'The 6- to 32-character password that you defined while registering for the account.',
                          'group_id' => '6'),
      				array('title' => 'PARTNER',
      					  'key' => 'MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_PARTNER',
      				      'value' => '',
      				      'description' => 'The ID provided to you by the authorised PayPal Reseller who registered you for the Payflow SDK. If you purchased your account directly from PayPal.',
      				      'group_id' => '6'),      		
                    array('title' => 'Transaction Server',
                          'key' => 'MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_CHECKOUT_TRANSACTION_SERVER',
                          'value' => 'Live',
                          'description' => 'Use the live or testing (sandbox) gateway server to process transactions?',
                          'group_id' => '6',
                          'set_function' => 'osc_cfg_set_boolean_value(array(\'Live\', \'Sandbox\'))'),
                    array('title' => 'Transaction Method',
                          'key' => 'MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_CHECKOUT_TRANSACTION_METHOD',
                          'value' => 'Sale',
                          'description' => 'The processing method to use for each transaction.',
                          'group_id' => '6',
                          'set_function' => 'osc_cfg_set_boolean_value(array(\'Authorization\', \'Sale\'))'),
                    array('title' => 'Debug E-Mail Address',
                          'key' => 'MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_CHECKOUT_DEBUG_EMAIL',
                          'value' => '',
                          'description' => 'All parameters of an invalid transaction will be sent to this email address.',
                          'group_id' => '6'),
                    array('title' => 'Payment Zone',
                          'key' => 'MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_CHECKOUT_ZONE',
                          'value' => '0',
                          'description' => 'If a zone is selected, only enable this payment method for that zone.',
                          'group_id' => '6',
                          'use_function' => 'osc_cfg_use_get_zone_class_title',
                          'set_function' => 'osc_cfg_set_zone_classes_pull_down_menu'),
                    array('title' => 'Sort order of display.',
                          'key' => 'MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_CHECKOUT_SORT_ORDER',
                          'value' => '0',
                          'description' => 'Sort order of display. Lowest is displayed first.',
                          'group_id' => '6'),
                    array('title' => 'Set Order Status',
                          'key' => 'MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_CHECKOUT_ORDER_STATUS_ID',
                          'value' => '0',
                          'description' => 'Set the status of orders made with this payment module to this value',
                          'group_id' => '6',
                          'use_function' => 'osc_cfg_use_get_order_status_title',
                          'set_function' => 'osc_cfg_set_order_statuses_pull_down_menu')
                   );

      OSCOM::callDB('Admin\InsertConfigurationParameters', $data, 'Site');
    }

/**
 * Return the configuration parameter keys in an array
 *
 * @access public
 * @return array
 */

    public function getKeys() {
      return array('MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_CHECKOUT_STATUS',
                   'MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_CHECKOUT_VENDOR',
                   'MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_USER',
                   'MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_PASSWORD',
      			   'MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_PARTNER',
                   'MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_CHECKOUT_TRANSACTION_SERVER',
                   'MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_CHECKOUT_TRANSACTION_METHOD',
                   'MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_CHECKOUT_DEBUG_EMAIL',
                   'MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_CHECKOUT_ZONE',
                   'MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_CHECKOUT_SORT_ORDER',
                   'MODULE_PAYMENT_PAYPAL_PAYFLOW_HOSTED_CHECKOUT_ORDER_STATUS_ID');
    }
  }
?>
