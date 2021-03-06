/*!
 Copyright (C) 2017 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */
(function (can, GGRC) {
  'use strict';

  var ALL_SAVED_TEXT = 'All changes saved';
  var UNSAVED_TEXT = 'Unsaved changes';
  var IS_SAVING_TEXT = 'Saving...';

  GGRC.Components('autoSaveFormStatus', {
    tag: 'auto-save-form-status',
    template: '{{formStatusText}}<content></content>',
    viewModel: {
      define: {
        isDirty: {
          type: 'boolean',
          value: false
        },
        formSaving: {
          type: 'boolean',
          value: false
        },
        formStatusText: {
          type: 'string',
          get: function () {
            if (this.attr('formSaving')) {
              return IS_SAVING_TEXT;
            }
            return !this.attr('isDirty') ? ALL_SAVED_TEXT : UNSAVED_TEXT;
          }
        }
      }
    }
  });
})(window.can, window.GGRC);
